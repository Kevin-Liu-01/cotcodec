"""Runtime of the Q3 K1 screen: staging, checkpoints, training, evaluation, statistics.

The entry point ``scripts/run_sparse_indexer_phase0a.py`` orchestrates these
pieces as a PID-1 parent with layer-sharded (training) or prompt-sharded
(evaluation) subprocess workers. Workers share no tensors and use no
collectives; they communicate only through files written atomically under the
run's ``checkpoints/`` directory, which is the directory a fresh resume job
receives (``resume_subpath``).

Persistent layout under ``<output>/checkpoints``::

    worker-<w>/step-<s>/{state.safetensors,meta.json}   two validated generations
    signal/<token>/worker-<w>.json                      signal-save acknowledgements
    devkl/worker-<w>.json                               stream-dev KL (all 18 indexers)
    lr_freeze.json                                      frozen LR per target (hashed)
    eval/<stage>/chunk-<i>.npz                          evaluation results per chunk
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import signal
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch

from harness import sparse_indexer_k1_stats as k1s
from harness import sparse_indexer_torch as sit

LEARNING_RATES: tuple[float, ...] = (3e-4, 1e-3, 3e-3)
PREFERRED_LR = 1e-3
LR_TIE_FRACTION = 0.01
ADAM_BETAS = (0.9, 0.999)
ADAM_EPS = 1e-8
GRAD_CLIP = 1.0
TARGET_ROW_CHUNK = 1024
EXIT_OK = 0
EXIT_CONTRACT = 2
EXIT_INTEGRITY = 3
EXIT_CHECKPOINTED = 75


class RuntimeContractError(RuntimeError):
    """Integrity failure during a run (exit code 3)."""


class CheckpointedExit(Exception):  # noqa: N818 - control flow, not an error
    """Raised inside a worker after a signal-triggered save completed."""


# --------------------------------------------------------------------------- #
# Profiles
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Profile:
    """Registered sizes. ``tiny`` exists only for the CPU doctor and tests."""

    name: str
    batch: int
    steps: int | None  # None: floor(train sequences / batch)
    warmup: int
    checkpoint_every: int
    k_blocks: int
    union_k: int
    union_budget_k: int
    eval_chunk: int

    @classmethod
    def registered(cls) -> Profile:
        return cls("registered", 4, 610, 20, 100, sit.BLOCK_BUDGET, sit.UNION_K_PER_HEAD,
                   sit.UNION_BUDGET_MATCHED_K, 64)

    @classmethod
    def tiny(cls) -> Profile:
        return cls("tiny", 2, None, 2, 2, 4, 16, 1, 8)


def lr_tag(lr: float) -> str:
    return f"{lr:.0e}".replace("-0", "-")


def indexer_key(target: str, lr: float, seed: int) -> str:
    return f"{target}|{lr_tag(lr)}|{seed}"


# --------------------------------------------------------------------------- #
# Atomic files and signals
# --------------------------------------------------------------------------- #


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload: Any) -> str:
    data = (json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n").encode()
    atomic_write_bytes(path, data)
    return hashlib.sha256(data).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value)}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SignalFlag:
    """Records SIGUSR1/SIGTERM; checked at safe points."""

    def __init__(self) -> None:
        self.received: str | None = None

    def install(self) -> None:
        signal.signal(signal.SIGUSR1, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def _handle(self, signum: int, _frame: Any) -> None:
        self.received = signal.Signals(signum).name


# --------------------------------------------------------------------------- #
# Staging (parent decodes the bundle once; workers memory-map arrays)
# --------------------------------------------------------------------------- #


def stage_bundle(bundle: Mapping[str, Any], stage_dir: Path) -> dict[str, Any]:
    from harness import sparse_indexer_data as sid

    stage_dir.mkdir(parents=True, exist_ok=True)
    arrays = {
        "train_tokens": bundle["stream"]["train_tokens"],
        "dev_tokens": bundle["stream"]["dev_tokens"],
        "context_tokens": bundle["eval"]["context_tokens"],
        "context_offsets": bundle["eval"]["context_offsets"],
        "query_tokens": bundle["eval"]["query_tokens"],
        "query_offsets": bundle["eval"]["query_offsets"],
        "option_tokens": bundle["eval"]["option_tokens"],
        "option_offsets": bundle["eval"]["option_offsets"],
    }
    digests = {}
    for name, payload in arrays.items():
        array = sid.decode_array(payload)
        np.save(stage_dir / f"{name}.npy", array, allow_pickle=False)
        digests[name] = payload["sha256"]
    meta = {
        "context_meta": bundle["eval"]["context_meta"],
        "query_meta": bundle["eval"]["query_meta"],
        "prompts": bundle["eval"]["prompts"],
        "split": bundle["split"],
        "digests": digests,
    }
    atomic_write_json(stage_dir / "meta.json", meta)
    return meta


class StagedData:
    def __init__(self, stage_dir: Path) -> None:
        self.dir = stage_dir
        self.meta = json.loads((stage_dir / "meta.json").read_text(encoding="utf-8"))

    def array(self, name: str) -> np.ndarray:
        return np.load(self.dir / f"{name}.npy", mmap_mode="r", allow_pickle=False)

    def prompt_tokens(self, prompt: Mapping[str, Any]) -> tuple[np.ndarray, int, int, int, int]:
        c_off, q_off = self.array("context_offsets"), self.array("query_offsets")
        ci, qi = int(prompt["context_index"]), int(prompt["query_index"])
        context = np.asarray(self.array("context_tokens")[c_off[ci] : c_off[ci + 1]])
        query = np.asarray(self.array("query_tokens")[q_off[qi] : q_off[qi + 1]])
        qmeta = self.meta["query_meta"][qi]
        cmeta = self.meta["context_meta"][ci]
        tokens = np.concatenate([context, query])
        q0 = len(context) + int(qmeta["row_start"])
        q1 = len(context) + int(qmeta["row_end"])
        return tokens, q0, q1, int(cmeta["needle_start"]), int(cmeta["needle_end"])

    def options(self, prompt: Mapping[str, Any]) -> tuple[list[np.ndarray], list[int], int]:
        o_off = self.array("option_offsets")
        o_tok = self.array("option_tokens")
        qmeta = self.meta["query_meta"][int(prompt["query_index"])]
        options = [np.asarray(o_tok[o_off[i] : o_off[i + 1]]) for i in qmeta["options"]]
        return options, list(qmeta["option_bytes"]), int(qmeta["correct"])


# --------------------------------------------------------------------------- #
# Checkpoint store
# --------------------------------------------------------------------------- #


class CheckpointStore:
    """Atomic generations ``step-<s>`` with digests; keeps the two latest valid ones."""

    def __init__(self, root: Path, keep: int = 2) -> None:
        self.root = root
        self.keep = keep

    def generations(self) -> list[int]:
        if not self.root.is_dir():
            return []
        steps = []
        for child in self.root.iterdir():
            if child.is_dir() and child.name.startswith("step-") and child.name[5:].isdigit():
                steps.append(int(child.name[5:]))
        return sorted(steps)

    def path(self, step: int) -> Path:
        return self.root / f"step-{step:06d}"

    def save(self, step: int, tensors: dict[str, torch.Tensor], meta: dict[str, Any]) -> str:
        from safetensors.torch import load_file, save_file

        final = self.path(step)
        temporary = self.root / f".tmp-step-{step:06d}-{os.getpid()}"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(parents=True)
        cpu = {name: t.detach().contiguous().cpu() for name, t in tensors.items()}
        digest = sit.state_digest(cpu)
        save_file(cpu, str(temporary / "state.safetensors"))
        reloaded = load_file(str(temporary / "state.safetensors"))
        if sit.state_digest(reloaded) != digest:
            raise RuntimeContractError("checkpoint does not reload bit-identically")
        meta = {**meta, "step": step, "state_digest": digest,
                "file_sha256": sha256_file(temporary / "state.safetensors")}
        atomic_write_json(temporary / "meta.json", meta)
        for handle_path in (temporary / "state.safetensors", temporary / "meta.json"):
            with handle_path.open("rb") as handle:
                os.fsync(handle.fileno())
        if final.exists():
            shutil.rmtree(final)
        os.replace(temporary, final)
        for old in self.generations()[: -self.keep]:
            shutil.rmtree(self.path(old), ignore_errors=True)
        return digest

    def load_latest(self) -> tuple[int, dict[str, torch.Tensor], dict[str, Any]] | None:
        from safetensors.torch import load_file

        for step in reversed(self.generations()):
            directory = self.path(step)
            try:
                meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
                if sha256_file(directory / "state.safetensors") != meta["file_sha256"]:
                    continue
                tensors = load_file(str(directory / "state.safetensors"))
                if sit.state_digest(tensors) != meta["state_digest"]:
                    continue
                return step, tensors, meta
            except (OSError, KeyError, ValueError, json.JSONDecodeError):
                continue
        return None


# --------------------------------------------------------------------------- #
# Indexer bank (one layer's 18 indexers with their optimisers)
# --------------------------------------------------------------------------- #


@dataclass
class TrainSpec:
    layers: list[int]
    seeds: list[int]
    targets: list[str]
    lrs: list[float]
    steps: int
    batch: int
    warmup: int
    checkpoint_every: int
    stop_after_step: int | None = None
    hold_after_step: int | None = None
    epochs: int = 1
    train_only: list[str] | None = None  # indexer keys to keep training (extension)
    accept_config_digests: list[str] | None = None  # earlier configs a resume may extend


class IndexerBank:
    def __init__(self, spec: sit.IndexerSpec, layers: Sequence[int], keys: Sequence[str],
                 device: torch.device) -> None:
        self.spec = spec
        self.layers = list(layers)
        self.keys = list(keys)
        self.device = device
        self.indexers: dict[tuple[int, str], sit.BlockIndexer] = {}
        self.optimisers: dict[tuple[int, str], torch.optim.Adam] = {}
        for layer in self.layers:
            for key in self.keys:
                target, lr_s, seed_s = key.split("|")
                indexer = sit.BlockIndexer.initialised(spec, int(seed_s), layer, target)
                indexer = indexer.to(device)
                self.indexers[(layer, key)] = indexer
                self.optimisers[(layer, key)] = torch.optim.Adam(
                    indexer.parameters(), lr=float(lr_s), betas=ADAM_BETAS, eps=ADAM_EPS,
                    weight_decay=0.0, foreach=False,
                )

    @staticmethod
    def lr_of(key: str) -> float:
        return float(key.split("|")[1])

    def state_tensors(self) -> dict[str, torch.Tensor]:
        out: dict[str, torch.Tensor] = {}
        for (layer, key), indexer in self.indexers.items():
            prefix = f"L{layer:02d}|{key}"
            for name, param in indexer.named_parameters():
                out[f"{prefix}|param|{name}"] = param.detach()
            opt_state = self.optimisers[(layer, key)].state
            for name, param in indexer.named_parameters():
                state = opt_state.get(param)
                if state:
                    out[f"{prefix}|exp_avg|{name}"] = state["exp_avg"]
                    out[f"{prefix}|exp_avg_sq|{name}"] = state["exp_avg_sq"]
                    out[f"{prefix}|step|{name}"] = torch.as_tensor(state["step"]).reshape(1)
        return out

    def load_state(self, tensors: Mapping[str, torch.Tensor]) -> None:
        for (layer, key), indexer in self.indexers.items():
            prefix = f"L{layer:02d}|{key}"
            optimiser = self.optimisers[(layer, key)]
            with torch.no_grad():
                for name, param in indexer.named_parameters():
                    param.copy_(tensors[f"{prefix}|param|{name}"].to(param.device))
            for name, param in indexer.named_parameters():
                avg = tensors.get(f"{prefix}|exp_avg|{name}")
                if avg is None:
                    continue
                optimiser.state[param] = {
                    "step": tensors[f"{prefix}|step|{name}"].reshape(()).clone().float().cpu(),
                    "exp_avg": avg.to(param.device).clone(),
                    "exp_avg_sq": tensors[f"{prefix}|exp_avg_sq|{name}"].to(param.device).clone(),
                }

    def param_digest(self) -> dict[str, str]:
        out = {}
        for (layer, key), indexer in self.indexers.items():
            out[f"L{layer:02d}|{key}"] = sit.state_digest(
                {n: p for n, p in indexer.named_parameters()})
        return out


def learning_rate(step: int, base: float, warmup: int) -> float:
    if warmup <= 0:
        return base
    return base * min(1.0, (step + 1) / warmup)


def sequence_targets(q: torch.Tensor, k: torch.Tensor, scaling: float,
                     chunk: int = TARGET_ROW_CHUNK) -> dict[str, torch.Tensor]:
    """hs and mp targets over every row of one sequence (chunked exact probabilities)."""

    length = k.shape[1]
    parts: dict[str, list[torch.Tensor]] = {"hs": [], "mp": [], "valid": []}
    for start in range(0, length, chunk):
        rows = torch.arange(start, min(start + chunk, length), device=k.device)
        probs = sit.head_probs_rows(q[:, start : start + len(rows)], k, rows, scaling)
        targets = sit.block_targets(probs, rows)
        for name in parts:
            parts[name].append(targets[name])
        del probs
    return {name: torch.cat(values) for name, values in parts.items()}


# --------------------------------------------------------------------------- #
# Training worker
# --------------------------------------------------------------------------- #


@dataclass
class WorkerContext:
    worker: int
    out_dir: Path
    ckpt_dir: Path
    stage: StagedData
    model_dir: Path
    device: torch.device
    flag: SignalFlag
    hashes: dict[str, str] = field(default_factory=dict)
    token_file: Path | None = None


def _signal_token(ctx: WorkerContext) -> str:
    request = ctx.ckpt_dir / "signal" / "request.json"
    try:
        return json.loads(request.read_text(encoding="utf-8"))["token"]
    except (OSError, KeyError, json.JSONDecodeError):
        return f"unrequested-{ctx.flag.received or 'none'}"


def _ack_signal(ctx: WorkerContext, payload: dict[str, Any]) -> None:
    token = _signal_token(ctx)
    atomic_write_json(ctx.ckpt_dir / "signal" / token / f"worker-{ctx.worker}.json",
                      {**payload, "token": token, "worker": ctx.worker,
                       "signal": ctx.flag.received})


def epoch_order(n: int, epoch: int) -> np.ndarray:
    """Epoch 1 keeps the bundle's order; epochs 2 and 3 use permutations seeded 43 and 44."""

    if epoch == 1:
        return np.arange(n)
    return np.random.default_rng(42 + epoch - 1).permutation(n)


def batch_indices(step: int, batch: int, n_sequences: int, steps_per_epoch: int) -> np.ndarray:
    epoch = step // steps_per_epoch + 1
    within = step % steps_per_epoch
    order = epoch_order(n_sequences, epoch)
    return order[within * batch : (within + 1) * batch]


def run_training_worker(ctx: WorkerContext, spec: TrainSpec, profile: Profile) -> dict:
    from harness.sparse_indexer_torch import CaptureSession, load_teacher

    sit.set_determinism(allow_tf32=True)
    teacher = load_teacher(ctx.model_dir, ctx.device, max_layer=max(spec.layers))
    config = teacher.config
    scaling = float(getattr(config, "head_dim", config.hidden_size // config.num_attention_heads)
                    ) ** -0.5
    ispec = sit.IndexerSpec(d_model=int(config.hidden_size))
    keys = [indexer_key(t, lr, s) for t in spec.targets for lr in spec.lrs for s in spec.seeds]
    trainable = set(spec.train_only or keys)
    bank = IndexerBank(ispec, spec.layers, keys, ctx.device)
    store = CheckpointStore(ctx.ckpt_dir / f"worker-{ctx.worker}")
    start_step = 0
    loaded = store.load_latest()
    resume_meta: dict[str, Any] | None = None
    if loaded is not None:
        start_step, tensors, resume_meta = loaded
        allowed = {config_digest(spec, profile, ctx.hashes), *(spec.accept_config_digests or [])}
        if resume_meta.get("config_digest") not in allowed:
            raise RuntimeContractError("checkpoint was written under a different configuration")
        bank.load_state(tensors)
    train_tokens = ctx.stage.array("train_tokens")
    n_train = int(train_tokens.shape[0])
    steps_per_epoch = n_train // spec.batch
    total_steps = spec.steps
    if total_steps > steps_per_epoch * spec.epochs:
        raise RuntimeContractError("not enough training sequences for the registered steps")
    loss_log = ctx.out_dir / f"train-loss-worker-{ctx.worker}.jsonl"
    timings: dict[str, float] = {"teacher_s": 0.0, "targets_s": 0.0, "indexers_s": 0.0}

    def save(step: int, reason: str) -> str:
        return store.save(step, bank.state_tensors(), {
            "reason": reason, "worker": ctx.worker, "layers": spec.layers,
            "config_digest": config_digest(spec, profile, ctx.hashes),
            "hashes": ctx.hashes, "parent_job_id": os.environ.get("SLURM_JOB_ID"),
            "epoch_rule": "epoch 1 bundle order; epochs 2-3 permutations seeded 43, 44",
        })

    def handle_signal(step: int) -> None:
        digest = save(step, f"signal-{ctx.flag.received}")
        _ack_signal(ctx, {"phase": "train", "step": step, "state_digest": digest})
        raise CheckpointedExit(step)

    step = start_step
    while step < total_steps:
        if spec.stop_after_step is not None and step >= spec.stop_after_step:
            break
        if ctx.flag.received:
            handle_signal(step)
        indices = batch_indices(step, spec.batch, n_train, steps_per_epoch)
        batch = torch.as_tensor(np.asarray(train_tokens[indices], dtype=np.int64),
                                device=ctx.device)
        started = time.perf_counter()
        with CaptureSession(teacher, spec.layers) as cap, torch.no_grad():
            teacher.model(input_ids=batch, use_cache=False)
            captured = {layer: (cap.query[layer], cap.key[layer], cap.hidden[layer])
                        for layer in spec.layers}
        _sync(ctx.device)
        timings["teacher_s"] += time.perf_counter() - started
        losses: dict[str, float] = {}
        for layer in spec.layers:
            q_all, k_all, h_all = captured[layer]
            for b in range(batch.shape[0]):
                started = time.perf_counter()
                with torch.no_grad():
                    targets = sequence_targets(q_all[b], k_all[b], scaling)
                _sync(ctx.device)
                timings["targets_s"] += time.perf_counter() - started
                started = time.perf_counter()
                rows = torch.arange(h_all.shape[1], device=ctx.device)
                hidden = h_all[b]
                for key in keys:
                    if key not in trainable:
                        continue
                    target_name = key.split("|")[0]
                    indexer = bank.indexers[(layer, key)]
                    scores, valid = indexer(hidden, rows)
                    loss, _ = sit.kl_block_loss(targets[target_name], scores, valid)
                    (loss / batch.shape[0]).backward()
                    losses[f"L{layer:02d}|{key}"] = losses.get(f"L{layer:02d}|{key}", 0.0) + (
                        float(loss.detach()) / batch.shape[0])
                _sync(ctx.device)
                timings["indexers_s"] += time.perf_counter() - started
                del targets
            for key in keys:
                if key not in trainable:
                    continue
                indexer = bank.indexers[(layer, key)]
                optimiser = bank.optimisers[(layer, key)]
                torch.nn.utils.clip_grad_norm_(indexer.parameters(), GRAD_CLIP, foreach=False)
                for group in optimiser.param_groups:
                    group["lr"] = learning_rate(step, bank.lr_of(key), spec.warmup)
                optimiser.step()
                optimiser.zero_grad(set_to_none=True)
        del captured
        if not all(math.isfinite(v) for v in losses.values()):
            raise RuntimeContractError(f"non-finite training loss at step {step}")
        with loss_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"step": step, "losses": losses}, sort_keys=True) + "\n")
        step += 1
        if ctx.flag.received:
            handle_signal(step)
        if step % spec.checkpoint_every == 0 and step < total_steps:
            save(step, "periodic")
        if spec.hold_after_step is not None and step == spec.hold_after_step:
            # Resume-test leg R1: idle at this step until the time-limit signal.
            atomic_write_json(ctx.ckpt_dir / "holding" / f"worker-{ctx.worker}.json",
                              {"worker": ctx.worker, "step": step})
            while not ctx.flag.received:
                time.sleep(0.5)
            handle_signal(step)
    final_step = step
    digest = save(final_step, "final" if final_step >= total_steps else "stop-after-step")
    return {"worker": ctx.worker, "final_step": final_step, "state_digest": digest,
            "param_digests": bank.param_digest(), "timings": timings,
            "resumed_from": resume_meta["step"] if resume_meta else None}


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def config_digest(spec: TrainSpec, profile: Profile, hashes: Mapping[str, str]) -> str:
    payload = {"layers": spec.layers, "seeds": spec.seeds, "targets": spec.targets,
               "lrs": spec.lrs, "steps": spec.steps, "batch": spec.batch,
               "warmup": spec.warmup, "epochs": spec.epochs, "profile": profile.name,
               "train_only": spec.train_only,
               "bundle": hashes.get("bundle_sha256"), "model": hashes.get("receipt_sha256")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def run_devkl_worker(ctx: WorkerContext, spec: TrainSpec) -> dict:
    """Mean stream-dev KL of every indexer on the worker's layers (no gradients)."""

    from harness.sparse_indexer_torch import CaptureSession, load_teacher

    sit.set_determinism(allow_tf32=True)
    teacher = load_teacher(ctx.model_dir, ctx.device, max_layer=max(spec.layers))
    config = teacher.config
    scaling = float(getattr(config, "head_dim", config.hidden_size // config.num_attention_heads)
                    ) ** -0.5
    ispec = sit.IndexerSpec(d_model=int(config.hidden_size))
    keys = [indexer_key(t, lr, s) for t in spec.targets for lr in spec.lrs for s in spec.seeds]
    bank = IndexerBank(ispec, spec.layers, keys, ctx.device)
    store = CheckpointStore(ctx.ckpt_dir / f"worker-{ctx.worker}")
    loaded = store.load_latest()
    if loaded is None or loaded[0] < spec.steps:
        raise RuntimeContractError("stream-dev KL needs the final training generation")
    bank.load_state(loaded[1])
    dev = ctx.stage.array("dev_tokens")
    sums = {f"L{layer:02d}|{key}": 0.0 for layer in spec.layers for key in keys}
    for index in range(dev.shape[0]):
        if ctx.flag.received:
            _ack_signal(ctx, {"phase": "devkl", "completed_sequences": index})
            raise CheckpointedExit(index)
        tokens = torch.as_tensor(np.asarray(dev[index : index + 1], dtype=np.int64),
                                 device=ctx.device)
        with CaptureSession(teacher, spec.layers) as cap, torch.no_grad():
            teacher.model(input_ids=tokens, use_cache=False)
            for layer in spec.layers:
                q, k, h = cap.query[layer][0], cap.key[layer][0], cap.hidden[layer][0]
                targets = sequence_targets(q, k, scaling)
                rows = torch.arange(h.shape[0], device=ctx.device)
                for key in keys:
                    scores, valid = bank.indexers[(layer, key)](h, rows)
                    loss, _ = sit.kl_block_loss(targets[key.split("|")[0]], scores, valid)
                    sums[f"L{layer:02d}|{key}"] += float(loss)
    result = {name: value / dev.shape[0] for name, value in sums.items()}
    if not all(math.isfinite(v) for v in result.values()):
        raise RuntimeContractError("non-finite stream-dev KL")
    payload = {"worker": ctx.worker, "sequences": int(dev.shape[0]), "kl": result}
    atomic_write_json(ctx.ckpt_dir / "devkl" / f"worker-{ctx.worker}.json", payload)
    return payload


def freeze_learning_rates(devkl: Sequence[Mapping[str, Any]], targets: Sequence[str],
                          lrs: Sequence[float], seeds: Sequence[int]) -> dict[str, Any]:
    """Per target: the LR with the lowest mean stream-dev KL over seeds and layers.

    Ties within 1 percent of the minimum go to 1e-3.
    """

    merged: dict[str, float] = {}
    for payload in devkl:
        merged.update(payload["kl"])
    table: dict[str, dict[str, float]] = {}
    chosen: dict[str, float] = {}
    for target in targets:
        means = {}
        for lr in lrs:
            values = [value for name, value in merged.items()
                      if name.split("|", 1)[1].startswith(f"{target}|{lr_tag(lr)}|")]
            expected = len(seeds) * len({name.split("|")[0] for name in merged})
            if len(values) != expected or not values:
                raise RuntimeContractError(f"stream-dev KL incomplete for {target} {lr}")
            means[lr_tag(lr)] = float(np.mean(values))
        best = min(means.values())
        preferred = lr_tag(PREFERRED_LR)
        if preferred in means and means[preferred] <= best * (1.0 + LR_TIE_FRACTION):
            pick = PREFERRED_LR
        else:
            pick = min(lrs, key=lambda lr: (means[lr_tag(lr)], lr))
        table[target] = means
        chosen[target] = pick
    return {"rule": "lowest mean stream-dev KL over seeds and layers; ties within 1% go to "
                    "1e-3", "mean_kl": table, "selected_lr": {t: lr_tag(v) for t, v in
                                                              chosen.items()},
            "selected_lr_value": chosen}


# --------------------------------------------------------------------------- #
# Evaluation worker
# --------------------------------------------------------------------------- #


SELECTORS_DENSE = ("T:hs", "T:mp", "T:hm", "U", "Uk", "rand")


def selector_names(seeds: Sequence[int], targets: Sequence[str] = sit.TRAINED_TARGETS,
                   with_indexers: bool = True) -> list[str]:
    names = list(SELECTORS_DENSE)
    if with_indexers:
        names += [f"I:{t}:{s}" for t in targets for s in seeds]
    return names


@dataclass
class EvalSpec:
    """One evaluation stage. ``units`` are unique (context, query) pairs; each
    carries a representative prompt id and whether it needs selection recall
    (``select``) and multiple-choice scoring (``mc``)."""

    stage: str  # audit-main | dev-headroom | smoke
    units: list[dict[str, Any]]
    seeds: list[int]
    with_indexers: bool
    lr_freeze_path: str | None
    lr_freeze_sha256: str | None
    train_layers: list[list[int]]


def plan_units(prompts: Sequence[Mapping[str, Any]], selection_roles: Iterable[str],
               mc_roles: Iterable[str], mc_conditions: Iterable[str]) -> tuple[
                   list[dict[str, Any]], dict[str, str]]:
    """Deduplicate prompts that share (context, query); merge their needs."""

    selection_roles, mc_roles, mc_conditions = set(selection_roles), set(mc_roles), set(
        mc_conditions)
    units: dict[str, dict[str, Any]] = {}
    prompt_to_unit: dict[str, str] = {}
    for prompt in prompts:
        unit = f"c{int(prompt['context_index'])}-q{int(prompt['query_index'])}"
        entry = units.setdefault(unit, {"unit": unit, "prompt_id": prompt["prompt_id"],
                                        "select": False, "mc": False})
        entry["select"] |= prompt["role"] in selection_roles
        entry["mc"] |= prompt["role"] in mc_roles and prompt["condition"] in mc_conditions
        prompt_to_unit[prompt["prompt_id"]] = unit
    return [units[key] for key in sorted(units)], prompt_to_unit


def load_selected_indexers(ctx: WorkerContext, spec: EvalSpec, n_layers: int,
                           ispec: sit.IndexerSpec) -> dict[tuple[int, str, int], sit.BlockIndexer]:
    if not spec.with_indexers:
        return {}

    assert spec.lr_freeze_path and spec.lr_freeze_sha256
    path = Path(spec.lr_freeze_path)
    if sha256_file(path) != spec.lr_freeze_sha256:
        raise RuntimeContractError("lr_freeze.json changed after it was frozen")
    freeze = json.loads(path.read_text(encoding="utf-8"))
    out: dict[tuple[int, str, int], sit.BlockIndexer] = {}
    for worker, layers in enumerate(spec.train_layers):
        store = CheckpointStore(ctx.ckpt_dir / f"worker-{worker}")
        loaded = store.load_latest()
        if loaded is None:
            raise RuntimeContractError(f"training worker {worker} has no final generation")
        tensors = loaded[1]
        for layer in layers:
            for target, lr_s in freeze["selected_lr"].items():
                for seed in spec.seeds:
                    indexer = sit.BlockIndexer(ispec)
                    prefix = f"L{layer:02d}|{target}|{lr_s}|{seed}|param|"
                    state = {name[len(prefix):]: value for name, value in tensors.items()
                             if name.startswith(prefix)}
                    indexer.load_state_dict(state)
                    out[(layer, target, seed)] = indexer.to(ctx.device).eval()
    if len({key[0] for key in out}) != n_layers:
        raise RuntimeContractError("selected indexers do not cover every layer")
    return out


def _option_scores(teacher: Any, cache: Any, last_logits: torch.Tensor,
                   options: Sequence[np.ndarray], option_bytes: Sequence[int], prefix: int,
                   device: torch.device) -> list[float]:
    scores = []
    first = torch.log_softmax(last_logits.float(), dim=-1)
    for tokens, n_bytes in zip(options, option_bytes, strict=True):
        ids = torch.as_tensor(np.asarray(tokens, dtype=np.int64), device=device)[None]
        total = float(first[int(ids[0, 0])])
        if ids.shape[1] > 1:
            out = teacher(input_ids=ids[:, :-1], past_key_values=cache, use_cache=True)
            logp = torch.log_softmax(out.logits[0].float(), dim=-1)
            total += float(logp.gather(1, ids[0, 1:, None]).sum())
        cache.crop(prefix)
        scores.append(total / max(int(n_bytes), 1))
    return scores


def run_eval_worker(ctx: WorkerContext, spec: EvalSpec, profile: Profile) -> dict:
    """Evaluate a prompt shard; writes one atomic npz per chunk under eval/<stage>."""

    from transformers import DynamicCache

    from harness.sparse_indexer_torch import CaptureSession, load_teacher

    sit.set_determinism(allow_tf32=True)
    teacher = load_teacher(ctx.model_dir, ctx.device)
    config = teacher.config
    n_layers = int(config.num_hidden_layers)
    scaling = float(getattr(config, "head_dim", config.hidden_size // config.num_attention_heads)
                    ) ** -0.5
    ispec = sit.IndexerSpec(d_model=int(config.hidden_size))
    indexers = load_selected_indexers(ctx, spec, n_layers, ispec)
    names = selector_names(spec.seeds, with_indexers=spec.with_indexers)
    prompts = {p["prompt_id"]: p for p in ctx.stage.meta["prompts"]}
    out_dir = ctx.ckpt_dir / "eval" / spec.stage
    out_dir.mkdir(parents=True, exist_ok=True)
    done = 0
    for chunk_start in range(0, len(spec.units), profile.eval_chunk):
        chunk_units = spec.units[chunk_start : chunk_start + profile.eval_chunk]
        chunk_ids = [unit["unit"] for unit in chunk_units]
        chunk_name = hashlib.sha256("|".join(chunk_ids).encode()).hexdigest()[:16]
        target_path = out_dir / f"chunk-{chunk_name}.npz"
        if target_path.exists():
            done += len(chunk_ids)
            continue
        if ctx.flag.received:
            _ack_signal(ctx, {"phase": f"eval-{spec.stage}", "completed_prompts": done})
            raise CheckpointedExit(done)
        recall = np.full((len(chunk_ids), n_layers, len(names)), np.nan, dtype=np.float32)
        ties = np.zeros((len(chunk_ids), len(names)), dtype=np.int32)
        max_selected = np.zeros(len(chunk_ids), dtype=np.int32)
        mc = np.full((len(chunk_ids), 4), np.nan, dtype=np.float32)
        correct = np.full(len(chunk_ids), -1, dtype=np.int32)
        for row, unit in enumerate(chunk_units):
            prompt = prompts[unit["prompt_id"]]
            tokens, q0, q1, n0, n1 = ctx.stage.prompt_tokens(prompt)
            do_select = bool(unit["select"]) and n1 > n0 >= 0
            do_mc = bool(unit["mc"])
            if not (do_select or do_mc):
                continue
            ids = torch.as_tensor(tokens.astype(np.int64), device=ctx.device)[None]
            rows = torch.arange(q0, q1, device=ctx.device)
            cache = DynamicCache(config=config) if do_mc else None
            layers = range(n_layers) if do_select else []
            with CaptureSession(teacher, layers, query_rows=rows) as cap, torch.no_grad():
                out = teacher(input_ids=ids, use_cache=do_mc, past_key_values=cache,
                              logits_to_keep=1)
                if do_select:
                    for layer in range(n_layers):
                        q = cap.query[layer][0]
                        k = cap.key[layer][0]
                        hidden = cap.hidden[layer][0]
                        probs = sit.head_probs_rows(q, k, rows, scaling)
                        dense = sit.block_targets(probs, rows, include_hm=True)
                        valid = dense["valid"]
                        for col, name in enumerate(names):
                            if name.startswith("T:"):
                                score = dense[name[2:]]
                                chosen = sit.select_top_blocks(score, valid, profile.k_blocks)
                                ties[row, col] += sit.boundary_ties(score, valid, profile.k_blocks)
                                values = sit.block_selection_recall(chosen, rows, n0, n1)
                                selected = (chosen >= 0).sum(dim=-1) * sit.BLOCK_SIZE + (
                                    rows + 1) % sit.BLOCK_SIZE
                                max_selected[row] = max(max_selected[row], int(selected.max()))
                            elif name == "U":
                                values = sit.union_topk_recall(probs, rows, profile.union_k,
                                                               n0, n1)
                            elif name == "Uk":
                                values = sit.union_topk_recall(probs, rows,
                                                               profile.union_budget_k, n0, n1)
                            elif name == "rand":
                                values = sit.random_block_recall(rows, n0, n1, profile.k_blocks)
                            else:
                                _, target, seed_s = name.split(":")
                                indexer = indexers[(layer, target, int(seed_s))]
                                scores, ivalid = indexer(hidden, rows)
                                chosen = sit.select_top_blocks(scores, ivalid, profile.k_blocks)
                                ties[row, col] += sit.boundary_ties(scores, ivalid,
                                                                    profile.k_blocks)
                                values = sit.block_selection_recall(chosen, rows, n0, n1)
                                selected = (chosen >= 0).sum(dim=-1) * sit.BLOCK_SIZE + (
                                    rows + 1) % sit.BLOCK_SIZE
                                max_selected[row] = max(max_selected[row], int(selected.max()))
                            recall[row, layer, col] = float(values.mean()) * 100.0
                        del probs, dense
                if do_mc:
                    with cap.paused():
                        options, option_bytes, answer = ctx.stage.options(prompt)
                        mc[row] = _option_scores(teacher, cache, out.logits[0, -1], options,
                                                 option_bytes, ids.shape[1], ctx.device)
                        correct[row] = answer
            del cache
        payload = {"unit_ids": np.asarray(chunk_ids), "recall": recall, "ties": ties,
                   "max_selected_tokens": max_selected, "mc_scores": mc, "mc_correct": correct,
                   "selectors": np.asarray(names)}
        buffer_path = out_dir / f".chunk-{chunk_name}.tmp-{os.getpid()}.npz"
        np.savez(buffer_path, **payload)
        with buffer_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(buffer_path, target_path)
        done += len(chunk_ids)
    return {"worker": ctx.worker, "stage": spec.stage, "prompts": done}


def collect_eval(ckpt_dir: Path, stage: str, prompt_to_unit: Mapping[str, str]) -> dict[str, Any]:
    """Merge chunk files; every unit appears exactly once and every prompt maps to one (V3)."""

    directory = ckpt_dir / "eval" / stage
    units: dict[str, dict[str, Any]] = {}
    selectors: list[str] | None = None
    for path in sorted(directory.glob("chunk-*.npz")):
        with np.load(path, allow_pickle=False) as data:
            names = [str(v) for v in data["selectors"]]
            if selectors is None:
                selectors = names
            elif names != selectors:
                raise RuntimeContractError("eval chunks disagree on selectors")
            for i, unit_id in enumerate(data["unit_ids"]):
                unit_id = str(unit_id)
                if unit_id in units:
                    raise RuntimeContractError(f"unit {unit_id} evaluated twice")
                units[unit_id] = {
                    "recall": np.asarray(data["recall"][i], dtype=np.float64),
                    "ties": np.asarray(data["ties"][i]),
                    "max_selected": int(data["max_selected_tokens"][i]),
                    "mc_scores": np.asarray(data["mc_scores"][i], dtype=np.float64),
                    "mc_correct": int(data["mc_correct"][i]),
                }
    missing = sorted({unit for unit in prompt_to_unit.values() if unit not in units})
    if missing:
        raise RuntimeContractError(f"{len(missing)} units missing from the eval ledger")
    rows = {prompt_id: units[unit] for prompt_id, unit in prompt_to_unit.items()}
    return {"selectors": selectors or [], "rows": rows, "units": len(units)}


# --------------------------------------------------------------------------- #
# Statistics assembly
# --------------------------------------------------------------------------- #


def prompt_recall(row: Mapping[str, Any], selectors: Sequence[str], name: str) -> float:
    """Mean over layers (each layer: mean over query rows) of one selector's recall."""

    values = row["recall"][:, list(selectors).index(name)]
    if not np.isfinite(values).all():
        raise RuntimeContractError(f"non-finite recall for selector {name}")
    return float(values.mean())


def mc_correct(row: Mapping[str, Any]) -> float:
    scores = row["mc_scores"]
    if row["mc_correct"] < 0 or not np.isfinite(scores).all():
        raise RuntimeContractError("missing multiple-choice scores")
    return 100.0 * float(int(np.argmax(scores)) == row["mc_correct"])


def build_family_table(prompts: Sequence[Mapping[str, Any]], results: Mapping[str, Any],
                       target: str, seeds: Sequence[int], role: str,
                       other_condition: str) -> tuple[k1s.FamilyTable, list[str]]:
    rows = results["rows"]
    selectors = results["selectors"]
    families: dict[str, dict[str, Mapping[str, Any]]] = {}
    for prompt in prompts:
        if prompt["role"] != role:
            continue
        families.setdefault(prompt["family_id"], {})[prompt["condition"]] = prompt
    pair_names = sorted({p["pair"] for f in families.values() for p in f.values()})
    clusters = sorted({p["cluster"] for f in families.values() for p in f.values()})
    pair, cluster = [], []
    ind_mn: list[list[float]] = [[] for _ in seeds]
    ind_cx: list[list[float]] = [[] for _ in seeds]
    tgt_mn, tgt_cx, rand_mn, rand_cx = [], [], [], []
    for family_id in sorted(families):
        members = families[family_id]
        if set(members) != {"MN", other_condition}:
            raise RuntimeContractError(f"family {family_id} is incomplete")
        mn, cx = rows[members["MN"]["prompt_id"]], rows[members[other_condition]["prompt_id"]]
        pair.append(pair_names.index(members["MN"]["pair"]))
        cluster.append(clusters.index(members["MN"]["cluster"]))
        for i, seed in enumerate(seeds):
            ind_mn[i].append(prompt_recall(mn, selectors, f"I:{target}:{seed}"))
            ind_cx[i].append(prompt_recall(cx, selectors, f"I:{target}:{seed}"))
        tgt_mn.append(prompt_recall(mn, selectors, f"T:{target}"))
        tgt_cx.append(prompt_recall(cx, selectors, f"T:{target}"))
        rand_mn.append(prompt_recall(mn, selectors, "rand"))
        rand_cx.append(prompt_recall(cx, selectors, "rand"))
    table = k1s.FamilyTable(
        pair=np.asarray(pair), cluster=np.asarray(cluster), ind_mn=np.asarray(ind_mn),
        ind_cx=np.asarray(ind_cx), tgt_mn=np.asarray(tgt_mn), tgt_cx=np.asarray(tgt_cx),
        rand_mn=np.asarray(rand_mn), rand_cx=np.asarray(rand_cx))
    return table, pair_names


def descriptive_tables(prompts: Sequence[Mapping[str, Any]], results: Mapping[str, Any],
                       role: str) -> dict[str, Any]:
    """Per pair and condition: mean recall of every selector; per layer for CX."""

    rows = results["rows"]
    selectors = results["selectors"]
    out: dict[str, Any] = {}
    for prompt in prompts:
        if prompt["role"] != role:
            continue
        row = rows[prompt["prompt_id"]]
        key = f"{prompt['pair']}|{prompt['condition']}"
        bucket = out.setdefault(key, {"n": 0, "sum": np.zeros(len(selectors)),
                                      "layer_sum": np.zeros_like(row["recall"])})
        bucket["n"] += 1
        bucket["sum"] += row["recall"].mean(axis=0)
        bucket["layer_sum"] += row["recall"]
    return {
        key: {"n": value["n"],
              "mean_recall": dict(zip(selectors, (value["sum"] / value["n"]).tolist(),
                                      strict=True)),
              "per_layer": {name: (value["layer_sum"][:, i] / value["n"]).tolist()
                            for i, name in enumerate(selectors)}}
        for key, value in sorted(out.items())
    }


def summarise_headroom(prompts: Sequence[Mapping[str, Any]], results: Mapping[str, Any],
                       targets: Sequence[str], present_role: str, absent_role: str,
                       replicates: int = k1s.BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    rows = results["rows"]
    selectors = results["selectors"]
    present = [p for p in prompts if p["role"] == present_role and p["condition"] == "CX"]
    pair_names = sorted({p["pair"] for p in present})
    cluster_names = sorted({p["cluster"] for p in present})
    pair = np.asarray([pair_names.index(p["pair"]) for p in present])
    cluster = np.asarray([cluster_names.index(p["cluster"]) for p in present])
    h1 = {}
    for target in targets:
        diff = np.asarray([prompt_recall(rows[p["prompt_id"]], selectors, f"T:{target}")
                           - prompt_recall(rows[p["prompt_id"]], selectors, "rand")
                           for p in present])
        h1[target] = k1s.macro_mean_interval(diff, pair, cluster, replicates).point
    accuracy = np.asarray([mc_correct(rows[p["prompt_id"]]) for p in present])
    h2a = k1s.macro_mean_interval(accuracy, pair, cluster, replicates)
    by_family = {p["family_id"]: p for p in present}
    absent = [p for p in prompts if p["role"] == absent_role]
    diffs, absent_clusters = [], []
    for p in absent:
        twin = by_family.get(p["family_id"])
        if twin is None:
            raise RuntimeContractError(f"needle-absent cell {p['prompt_id']} has no twin")
        diffs.append(mc_correct(rows[twin["prompt_id"]]) - mc_correct(rows[p["prompt_id"]]))
        absent_clusters.append(p["cluster"])
    names = sorted(set(absent_clusters))
    h2b = k1s.macro_mean_interval(np.asarray(diffs), np.zeros(len(diffs), dtype=np.int64),
                                  np.asarray([names.index(c) for c in absent_clusters]),
                                  replicates)
    return {"h1_by_target": h1, "h1_points": max(h1.values()), "h2a": h2a, "h2b": h2b,
            "absent_accuracy": float(np.mean([mc_correct(rows[p["prompt_id"]])
                                              for p in absent])) if absent else None}


def interval_dict(interval: k1s.Interval) -> dict[str, Any]:
    return asdict(interval)


def iter_chunks(values: Sequence[Any], n: int) -> Iterable[list[Any]]:
    for start in range(0, len(values), n):
        yield list(values[start : start + n])


__all__ = [
    "EXIT_CHECKPOINTED",
    "EXIT_CONTRACT",
    "EXIT_INTEGRITY",
    "EXIT_OK",
    "LEARNING_RATES",
    "CheckpointStore",
    "CheckpointedExit",
    "EvalSpec",
    "IndexerBank",
    "Profile",
    "RuntimeContractError",
    "SignalFlag",
    "StagedData",
    "TrainSpec",
    "WorkerContext",
    "atomic_write_json",
    "batch_indices",
    "build_family_table",
    "collect_eval",
    "config_digest",
    "descriptive_tables",
    "epoch_order",
    "freeze_learning_rates",
    "indexer_key",
    "learning_rate",
    "lr_tag",
    "plan_units",
    "run_devkl_worker",
    "run_eval_worker",
    "run_training_worker",
    "selector_names",
    "sequence_targets",
    "sha256_file",
    "stage_bundle",
    "summarise_headroom",
]
