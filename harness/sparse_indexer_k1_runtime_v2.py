"""Runtime of the K1 successor screen (q3-k1-localization-screen-v2).

The workers of v1's runtime (``harness/sparse_indexer_k1_runtime.py``), with
the batched bank of ``harness/sparse_indexer_bank.py`` in place of the
per-indexer loop and a vectorised evaluation. Everything else is v1's code,
imported unchanged: staging, the checkpoint store with completion records, the
signal acknowledgements, the stream order, the LR freeze, the evaluation chunk
files and every statistic. Checkpoints keep v1's per-indexer tensor names, so
``scripts/compare_sparse_indexer_resume.py`` compares v2 resume legs as it
compares v1's.

What changes, and why it does not change a registered quantity:

* Training: one ``LayerBank`` per layer holds the trainable indexers; targets
  and the KL are computed per 1,024-row chunk over keys ``[0, chunk end)``
  (``harness/sparse_indexer_bank.py``). Losses stay on the device until one
  host copy per step. In the V1 extension, the indexers that are not trained
  are not in any bank: their parameters and Adam moments are carried through
  every checkpoint unchanged.
* Stream-dev KL: the same chunked KL without gradients, all 18 indexers of a
  layer at once.
* Evaluation: one teacher forward per unit as in v1; per layer the dense
  probabilities and targets are v1's own functions; the 9 block selectors
  (3 dense, 6 indexers) of ``EVAL_LAYER_GROUP`` layers are ranked by one
  ``torch.topk``; ``U`` and ``U_k`` share one top-k; the random baseline is
  computed once per unit (it does not depend on the layer); recall is
  accumulated on the device and copied to the host once per unit. The
  multiple-choice scores are v1's ``_option_scores``.
* Timing: every step and every unit is timed (with one device synchronisation
  per layer and per unit) so the smoke and the throughput probe measure the
  same code path that the main job runs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from harness import sparse_indexer_bank as skb
from harness import sparse_indexer_k1_runtime as rt
from harness import sparse_indexer_torch as sit
from harness.sparse_indexer_k1_runtime import (
    CheckpointedExit,
    CheckpointStore,
    EvalSpec,
    Profile,
    RuntimeContractError,
    TrainSpec,
    WorkerContext,
)

ENGINE = "k1-batched-bank-v2"


def config_digest(spec: TrainSpec, profile: Profile, hashes: Mapping[str, str]) -> str:
    """v1's configuration digest plus the engine and its fixed row chunk.

    A checkpoint written by another engine or chunk size is refused on resume.
    """

    payload = {"layers": spec.layers, "seeds": spec.seeds, "targets": spec.targets,
               "lrs": spec.lrs, "steps": spec.steps, "batch": spec.batch,
               "warmup": spec.warmup, "epochs": spec.epochs, "profile": profile.name,
               "train_only": spec.train_only, "engine": ENGINE, "row_chunk": skb.ROW_CHUNK,
               "bundle": hashes.get("bundle_sha256"), "model": hashes.get("receipt_sha256")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def teacher_scaling(config: Any) -> float:
    return float(getattr(config, "head_dim", config.hidden_size // config.num_attention_heads)
                 ) ** -0.5


# --------------------------------------------------------------------------- #
# A training worker's indexers
# --------------------------------------------------------------------------- #


class WorkerBanks:
    """One ``LayerBank`` per layer for the trainable keys, plus carried state of the rest."""

    def __init__(self, ispec: sit.IndexerSpec, layers: Sequence[int], keys: Sequence[str],
                 trainable: set[str], device: torch.device) -> None:
        unknown = trainable - set(keys)
        if unknown:
            raise RuntimeContractError(f"train_only names unknown indexers {sorted(unknown)}")
        self.layers = list(layers)
        self.keys = list(keys)
        self.trainable = [key for key in keys if key in trainable]
        self.frozen_keys = [key for key in keys if key not in trainable]
        self.banks = {layer: skb.LayerBank(ispec, layer, self.trainable, device)
                      for layer in self.layers} if self.trainable else {}
        self.frozen: dict[str, torch.Tensor] = {}
        for layer in self.layers:
            self.frozen.update(skb.initial_state(ispec, layer, self.frozen_keys))

    def _frozen_prefixes(self) -> list[str]:
        return [skb.slot_name(layer, key) for layer in self.layers for key in self.frozen_keys]

    def state_tensors(self) -> dict[str, torch.Tensor]:
        out = dict(self.frozen)
        for bank in self.banks.values():
            out.update(bank.state_tensors())
        return out

    def load_state(self, tensors: Mapping[str, torch.Tensor]) -> None:
        for bank in self.banks.values():
            bank.load_state(tensors)
        prefixes = tuple(f"{prefix}|" for prefix in self._frozen_prefixes())
        carried = {name: value.clone() for name, value in tensors.items()
                   if name.startswith(prefixes)}
        for prefix in self._frozen_prefixes():
            for name in skb.PARAM_NAMES:
                if f"{prefix}|param|{name}" not in carried:
                    raise RuntimeContractError(f"checkpoint lacks {prefix}|param|{name}")
        self.frozen = carried

    def param_digests(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for bank in self.banks.values():
            out.update(bank.param_digests())
        for prefix in self._frozen_prefixes():
            out[prefix] = sit.state_digest({name: self.frozen[f"{prefix}|param|{name}"]
                                            for name in skb.PARAM_NAMES})
        return dict(sorted(out.items()))


# --------------------------------------------------------------------------- #
# One training step (shared by the training worker, the smoke and the probe)
# --------------------------------------------------------------------------- #


def train_step(teacher: Any, layers: Sequence[int], banks: WorkerBanks, batch: torch.Tensor,
               step: int, warmup: int, scaling: float, device: torch.device,
               *, row_chunk: int = skb.ROW_CHUNK) -> tuple[dict[int, torch.Tensor],
                                                           dict[str, Any]]:
    """Teacher capture, every layer's bank forward/backward, clip and Adam.

    Returns per-layer per-slot losses (device tensors) and the step's timing:
    the teacher forward and each layer (targets, bank, clip and Adam for the
    batch), each closed by a device synchronisation.
    """

    started = time.perf_counter()
    with sit.CaptureSession(teacher, layers) as cap, torch.no_grad():
        teacher.model(input_ids=batch, use_cache=False)
        captured = {layer: (cap.query[layer], cap.key[layer], cap.hidden[layer])
                    for layer in layers}
    _sync(device)
    timing: dict[str, Any] = {"step": step, "teacher_s": time.perf_counter() - started,
                              "layers_s": {}}
    losses: dict[int, torch.Tensor] = {}
    sequences = batch.shape[0]
    for layer in layers:
        layer_started = time.perf_counter()
        bank = banks.banks.get(layer)
        if bank is not None:
            q_all, k_all, h_all = captured[layer]
            params = bank.working_params()
            total = None
            for b in range(sequences):
                kl = bank.accumulate_sequence(
                    params, h_all[b], skb.truncated_targets(q_all[b], k_all[b], scaling),
                    grad_scale=1.0 / sequences, row_chunk=row_chunk)
                total = kl if total is None else total + kl
            bank.adopt_grads(params)
            del params
            bank.clip_()
            bank.step(step, warmup)
            assert total is not None
            losses[layer] = total / sequences
        _sync(device)
        timing["layers_s"][str(layer)] = time.perf_counter() - layer_started
    del captured
    return losses, timing


def steady_mean(values: Sequence[float], skip: int) -> float | None:
    kept = list(values)[skip:]
    return float(np.mean(kept)) if kept else None


def summarise_steps(records: Sequence[Mapping[str, Any]], skip: int) -> dict[str, Any]:
    """Steady-state means (the first ``skip`` steps excluded) of a worker's step records."""

    kept = list(records)[skip:]
    if not kept:
        return {"steps_measured": 0}
    layers = sorted({layer for record in kept for layer in record["layers_s"]}, key=int)
    layer_means = {layer: float(np.mean([r["layers_s"][layer] for r in kept])) for layer in layers}
    step = float(np.mean([r["step_s"] for r in kept]))
    teacher = float(np.mean([r["teacher_s"] for r in kept]))
    return {"steps_measured": len(kept), "steps_skipped": skip, "step_s": step,
            "teacher_s": teacher, "layer_s": layer_means,
            "layers_total_s": float(sum(layer_means.values())),
            "overhead_s": step - teacher - float(sum(layer_means.values())),
            "step_s_all": [float(r["step_s"]) for r in records]}


# --------------------------------------------------------------------------- #
# Training worker
# --------------------------------------------------------------------------- #


def run_training_worker(ctx: WorkerContext, spec: TrainSpec, profile: Profile, *,
                        spawned_at: float | None = None) -> dict[str, Any]:
    """v1's training worker (resume, signals, hold, completion record) on the bank."""

    sit.set_determinism(allow_tf32=True)
    teacher = sit.load_teacher(ctx.model_dir, ctx.device, max_layer=max(spec.layers))
    scaling = teacher_scaling(teacher.config)
    ispec = sit.IndexerSpec(d_model=int(teacher.config.hidden_size))
    keys = [rt.indexer_key(t, lr, s) for t in spec.targets for lr in spec.lrs for s in spec.seeds]
    trainable = set(spec.train_only or keys)
    banks = WorkerBanks(ispec, spec.layers, keys, trainable, ctx.device)
    store = CheckpointStore(ctx.ckpt_dir / f"worker-{ctx.worker}")
    start_step = 0
    loaded = store.load_latest()
    resume_meta: dict[str, Any] | None = None
    current_config = config_digest(spec, profile, ctx.hashes)
    load_s = 0.0
    if loaded is not None:
        load_started = time.perf_counter()
        start_step, tensors, resume_meta = loaded
        earlier = set(spec.accept_config_digests or [])
        written_under = resume_meta.get("config_digest")
        if written_under != current_config:
            if written_under not in earlier:
                raise RuntimeContractError(
                    "checkpoint was written under a different configuration")
            # Continuing an earlier run (the V1 extension): only from the exact
            # generation that run completed, never from an older fallback.
            tensors, resume_meta = rt.load_completed_generation(ctx.ckpt_dir, ctx.worker,
                                                                start_step)
        banks.load_state(tensors)
        del tensors
        load_s = time.perf_counter() - load_started
    train_tokens = ctx.stage.array("train_tokens")
    n_train = int(train_tokens.shape[0])
    steps_per_epoch = n_train // spec.batch
    total_steps = spec.steps
    if total_steps > steps_per_epoch * spec.epochs:
        raise RuntimeContractError("not enough training sequences for the registered steps")
    loss_log = ctx.out_dir / f"train-loss-worker-{ctx.worker}.jsonl"
    timing_log = ctx.out_dir / f"train-timing-worker-{ctx.worker}.jsonl"
    records: list[dict[str, Any]] = []
    save_s: list[float] = []

    def save(step: int, reason: str) -> str:
        started = time.perf_counter()
        digest = store.save(step, banks.state_tensors(), {
            "reason": reason, "worker": ctx.worker, "layers": spec.layers,
            "config_digest": current_config, "engine": ENGINE,
            "hashes": ctx.hashes, "parent_job_id": os.environ.get("SLURM_JOB_ID"),
            "epoch_rule": "epoch 1 bundle order; epochs 2-3 permutations seeded 43, 44",
        })
        save_s.append(time.perf_counter() - started)
        return digest

    def handle_signal(step: int) -> None:
        digest = save(step, f"signal-{ctx.flag.received}")
        rt._ack_signal(ctx, {"phase": "train", "step": step, "state_digest": digest})
        raise CheckpointedExit(step)

    startup_s = time.time() - spawned_at if spawned_at is not None else None
    step = start_step
    while step < total_steps:
        if spec.stop_after_step is not None and step >= spec.stop_after_step:
            break
        if ctx.flag.received:
            handle_signal(step)
        step_started = time.perf_counter()
        indices = rt.batch_indices(step, spec.batch, n_train, steps_per_epoch)
        batch = torch.as_tensor(np.asarray(train_tokens[indices], dtype=np.int64),
                                device=ctx.device)
        layer_losses, timing = train_step(teacher, spec.layers, banks, batch, step,
                                          spec.warmup, scaling, ctx.device)
        losses: dict[str, float] = {}
        for layer, values in layer_losses.items():
            bank = banks.banks[layer]
            for key, value in zip(bank.keys, values.tolist(), strict=True):
                losses[skb.slot_name(layer, key)] = float(value)
        if not all(math.isfinite(v) for v in losses.values()):
            raise RuntimeContractError(f"non-finite training loss at step {step}")
        with loss_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"step": step, "losses": losses}, sort_keys=True) + "\n")
        timing["step_s"] = time.perf_counter() - step_started
        records.append(timing)
        with timing_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(timing, sort_keys=True) + "\n")
        step += 1
        if ctx.flag.received:
            handle_signal(step)
        if step % spec.checkpoint_every == 0 and step < total_steps:
            save(step, "periodic")
        if spec.hold_after_step is not None and step == spec.hold_after_step:
            # Resume-test leg R1: idle at this step until the time-limit signal.
            rt.atomic_write_json(ctx.ckpt_dir / "holding" / f"worker-{ctx.worker}.json",
                                 {"worker": ctx.worker, "step": step})
            while not ctx.flag.received:
                time.sleep(0.5)
            handle_signal(step)
    final_step = step
    reason = "final" if final_step >= total_steps else "stop-after-step"
    digest = save(final_step, reason)
    rt.write_completion_record(ctx.ckpt_dir, ctx.worker, final_step, digest, current_config,
                               reason)
    return {"worker": ctx.worker, "final_step": final_step, "state_digest": digest,
            "param_digests": banks.param_digests(), "engine": ENGINE,
            "timings": {"startup_s": startup_s, "load_s": load_s, "save_s": save_s,
                        "steps": summarise_steps(records, 0)},
            "step_records": records,
            "resumed_from": resume_meta["step"] if resume_meta else None}


# --------------------------------------------------------------------------- #
# Stream-dev KL worker
# --------------------------------------------------------------------------- #


def devkl_sequence(teacher: Any, layers: Sequence[int], params: Mapping[int, Mapping[str, Any]],
                   runs: Sequence[tuple[int, int, str]], ispec: sit.IndexerSpec,
                   tokens: torch.Tensor, scaling: float, device: torch.device
                   ) -> tuple[dict[int, torch.Tensor], dict[str, Any]]:
    """Per-layer, per-slot KL of one stream-dev sequence (no gradients), with timing."""

    started = time.perf_counter()
    with sit.CaptureSession(teacher, layers) as cap, torch.no_grad():
        teacher.model(input_ids=tokens, use_cache=False)
        captured = {layer: (cap.query[layer][0], cap.key[layer][0], cap.hidden[layer][0])
                    for layer in layers}
    _sync(device)
    timing: dict[str, Any] = {"teacher_s": time.perf_counter() - started, "layers_s": {}}
    out: dict[int, torch.Tensor] = {}
    for layer in layers:
        layer_started = time.perf_counter()
        q, k, h = captured[layer]
        out[layer] = skb.sequence_kl(params[layer], ispec, runs, h,
                                     skb.truncated_targets(q, k, scaling))
        _sync(device)
        timing["layers_s"][str(layer)] = time.perf_counter() - layer_started
    return out, timing


def add_sequence_kl(sums: dict[int, torch.Tensor | None],
                    values: Mapping[int, torch.Tensor]) -> None:
    """Add one sequence's per-slot KL to the running sums in float64.

    v1 adds ``float(loss)`` (each sequence's float32 loss, widened exactly) in
    Python floats; widening every float32 value before the sum and adding in
    the same sequence order gives v1's float64 sums bit for bit.
    """

    for layer, value in values.items():
        wide = value.detach().to(torch.float64)
        current = sums.get(layer)
        sums[layer] = wide if current is None else current + wide


def mean_sequence_kl(total: torch.Tensor | None, n_dev: int) -> list[float]:
    """v1's mean: the float64 sum divided by the number of sequences."""

    return [] if total is None else [float(value) for value in (total / n_dev).tolist()]


def run_devkl_worker(ctx: WorkerContext, spec: TrainSpec, *, spawned_at: float | None = None,
                     max_sequences: int | None = None) -> dict[str, Any]:
    """Mean stream-dev KL of every indexer on the worker's layers (v1 semantics).

    ``max_sequences`` (smoke timing only) evaluates a prefix of the stream-dev
    set and writes no ``devkl/worker-<w>.json``.
    """

    sit.set_determinism(allow_tf32=True)
    teacher = sit.load_teacher(ctx.model_dir, ctx.device, max_layer=max(spec.layers))
    scaling = teacher_scaling(teacher.config)
    ispec = sit.IndexerSpec(d_model=int(teacher.config.hidden_size))
    keys = [rt.indexer_key(t, lr, s) for t in spec.targets for lr in spec.lrs for s in spec.seeds]
    tensors, _ = rt.load_completed_generation(ctx.ckpt_dir, ctx.worker, spec.steps)
    params = {layer: skb.stack_from_state(tensors, layer, keys, ctx.device)
              for layer in spec.layers}
    del tensors
    runs = skb.target_runs([key.split("|")[0] for key in keys])
    dev = ctx.stage.array("dev_tokens")
    n_dev = int(dev.shape[0]) if max_sequences is None else min(int(dev.shape[0]), max_sequences)
    sums = {layer: None for layer in spec.layers}
    startup_s = time.time() - spawned_at if spawned_at is not None else None
    records = []
    for index in range(n_dev):
        if ctx.flag.received:
            rt._ack_signal(ctx, {"phase": "devkl", "completed_sequences": index})
            raise CheckpointedExit(index)
        tokens = torch.as_tensor(np.asarray(dev[index : index + 1], dtype=np.int64),
                                 device=ctx.device)
        values, timing = devkl_sequence(teacher, spec.layers, params, runs, ispec, tokens,
                                        scaling, ctx.device)
        records.append(timing)
        add_sequence_kl(sums, values)
    result: dict[str, float] = {}
    for layer in spec.layers:
        for key, value in zip(keys, mean_sequence_kl(sums[layer], n_dev), strict=True):
            result[skb.slot_name(layer, key)] = value
    if not all(math.isfinite(v) for v in result.values()):
        raise RuntimeContractError("non-finite stream-dev KL")
    payload = {"worker": ctx.worker, "sequences": n_dev, "kl": result}
    if max_sequences is None:
        rt.atomic_write_json(ctx.ckpt_dir / "devkl" / f"worker-{ctx.worker}.json", payload)
    return {**payload, "engine": ENGINE,
            "timings": {"startup_s": startup_s, "sequences": records}}


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #


@dataclass
class UnitOutput:
    recall: np.ndarray  # (layers, selectors) float32, NaN where the unit has no selection
    ties: np.ndarray  # (selectors,) int32
    max_selected: int
    mc_scores: np.ndarray  # (4,) float32, NaN without multiple choice
    mc_correct: int


def eval_keys(freeze: Mapping[str, Any], seeds: Sequence[int],
              targets: Sequence[str] = sit.TRAINED_TARGETS) -> list[str]:
    """The frozen-LR indexers in selector order (``I:<target>:<seed>``)."""

    return [f"{target}|{freeze['selected_lr'][target]}|{seed}" for target in targets
            for seed in seeds]


def load_eval_params(ctx: WorkerContext, spec: EvalSpec, n_layers: int
                     ) -> dict[int, dict[str, torch.Tensor]]:
    """v1 ``load_selected_indexers`` semantics, stacked per layer in selector order."""

    if not spec.with_indexers:
        return {}
    if not (spec.lr_freeze_path and spec.lr_freeze_sha256):
        raise RuntimeContractError("an indexer evaluation needs the hashed LR freeze")
    if spec.final_step is None:
        raise RuntimeContractError("an indexer evaluation needs the registered final step")
    path = Path(spec.lr_freeze_path)
    if rt.sha256_file(path) != spec.lr_freeze_sha256:
        raise RuntimeContractError("lr_freeze.json changed after it was frozen")
    freeze = json.loads(path.read_text(encoding="utf-8"))
    keys = eval_keys(freeze, spec.seeds)
    out: dict[int, dict[str, torch.Tensor]] = {}
    for worker, layers in enumerate(spec.train_layers):
        # Exactly the generation training completed at the registered final step.
        tensors, _ = rt.load_completed_generation(ctx.ckpt_dir, worker, spec.final_step)
        for layer in layers:
            out[layer] = skb.stack_from_state(tensors, layer, keys, ctx.device)
        del tensors
    if sorted(out) != list(range(n_layers)):
        raise RuntimeContractError("selected indexers do not cover every layer")
    return out


def evaluate_unit(teacher: Any, tokens: np.ndarray, q0: int, q1: int, n0: int, n1: int, *,
                  do_select: bool, do_mc: bool, options: Sequence[np.ndarray] = (),
                  option_bytes: Sequence[int] = (), answer: int = -1,
                  eval_params: Mapping[int, Mapping[str, torch.Tensor]] | None,
                  n_selectors: int, profile: Profile, scaling: float,
                  ispec: sit.IndexerSpec, device: torch.device) -> UnitOutput:
    """One evaluation unit: v1's outputs, computed with one host copy."""

    from transformers import DynamicCache

    config = teacher.config
    n_layers = int(config.num_hidden_layers)
    recall = np.full((n_layers, n_selectors), np.nan, dtype=np.float32)
    ties = np.zeros(n_selectors, dtype=np.int32)
    max_selected = 0
    mc = np.full(4, np.nan, dtype=np.float32)
    correct = -1
    ids = torch.as_tensor(tokens.astype(np.int64), device=device)[None]
    rows = torch.arange(q0, q1, device=device)
    cache = DynamicCache(config=config) if do_mc else None
    layers = range(n_layers) if do_select else []
    with sit.CaptureSession(teacher, layers, query_rows=rows) as cap, torch.no_grad():
        out = teacher(input_ids=ids, use_cache=do_mc, past_key_values=cache, logits_to_keep=1)
        if do_select:
            values, tie_counts, selected, finite = _select_unit(
                cap, rows, q0, n0, n1, eval_params, n_layers, n_selectors, profile, scaling,
                ispec)
            host = torch.cat([values.flatten(), tie_counts.double(), selected.double().reshape(1),
                              finite.double().reshape(1)]).cpu().numpy()
            if host[-1] != 1.0:
                raise RuntimeContractError("non-finite score on a selection prompt")
            recall[:] = host[: n_layers * n_selectors].reshape(n_layers, n_selectors)
            ties[:] = host[n_layers * n_selectors : n_layers * n_selectors + n_selectors]
            max_selected = int(host[-2])
        if do_mc:
            with cap.paused():
                mc[:] = rt._option_scores(teacher, cache, out.logits[0, -1], options,
                                          option_bytes, ids.shape[1], device)
                correct = int(answer)
    del cache
    return UnitOutput(recall, ties, max_selected, mc, correct)


def _select_unit(cap: Any, rows: torch.Tensor, q0: int, n0: int, n1: int,
                 eval_params: Mapping[int, Mapping[str, torch.Tensor]] | None, n_layers: int,
                 n_selectors: int, profile: Profile, scaling: float, ispec: sit.IndexerSpec
                 ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """``(layers, selectors)`` recall in percent, tie counts summed over layers, the
    most tokens any selection kept, and whether every score was finite.

    Selector columns follow v1's ``selector_names``: T:hs, T:mp, T:hm, U, Uk,
    rand, then the indexers. Tensors are assembled by concatenation only (no
    indexed writes on the device).
    """

    device = rows.device
    needle = n1 - n0
    finite = torch.ones((), dtype=torch.bool, device=device)
    random_percent = sit.random_block_recall(rows, n0, n1, profile.k_blocks).double().mean() * 100.0
    layer_rows: list[torch.Tensor] = []
    block_ties = None
    selected = torch.zeros((), dtype=torch.int64, device=device)
    for group_start in range(0, n_layers, skb.EVAL_LAYER_GROUP):
        group = range(group_start, min(group_start + skb.EVAL_LAYER_GROUP, n_layers))
        planes, unions = [], []
        valid = None
        for layer in group:
            q = cap.query[layer][0]
            k = cap.key[layer][0]
            probs = skb.causal_probs(q, k, rows, scaling)
            finite = finite & torch.isfinite(probs).all()
            dense = sit.block_targets(probs, rows, include_hm=True)
            valid = dense["valid"]
            big, small = skb.union_hits(probs, rows, (profile.union_k, profile.union_budget_k),
                                        n0, n1, min_row=q0)
            unions.append(torch.stack([skb.row_mean_percent(big, needle),
                                       skb.row_mean_percent(small, needle), random_percent]))
            layer_planes = [dense["hs"], dense["mp"], dense["hm"]]
            if eval_params:
                hidden = cap.hidden[layer][0]
                params = eval_params[layer]
                keys = skb.stacked_block_keys(params, hidden, ispec)
                scores = skb.stacked_scores(params, hidden[q0 : q0 + rows.numel()], rows, keys,
                                            ispec)
                layer_planes.extend(scores.float().unbind(0))
            planes.append(torch.stack([plane.float() for plane in layer_planes]))
            del probs
        assert valid is not None
        stacked = torch.stack(planes)  # (layers in group, block selectors, R, nB)
        finite = finite & (torch.isfinite(stacked) | ~valid).all()
        selection = skb.select_blocks(stacked, valid, rows, n0, n1, profile.k_blocks,
                                      min_row=q0)
        blocks = skb.row_mean_percent(selection.hits, needle)  # (layers in group, selectors)
        for offset in range(len(group)):
            layer_rows.append(torch.cat([blocks[offset, :3], unions[offset],
                                         blocks[offset, 3:]]))
        group_ties = selection.ties.sum(dim=0)
        block_ties = group_ties if block_ties is None else block_ties + group_ties
        selected = torch.maximum(selected, selection.selected_max.max())
    assert block_ties is not None
    recall = torch.stack(layer_rows)
    ties = torch.cat([block_ties[:3], torch.zeros(3, dtype=block_ties.dtype, device=device),
                      block_ties[3:]])
    if recall.shape != (n_layers, n_selectors):
        raise RuntimeContractError("selector columns do not match the registered selectors")
    return recall, ties, selected, finite


def run_eval_worker(ctx: WorkerContext, spec: EvalSpec, profile: Profile, *,
                    spawned_at: float | None = None) -> dict[str, Any]:
    """Evaluate a unit shard; writes v1's chunk files under ``eval/<stage>``."""

    sit.set_determinism(allow_tf32=True)
    teacher = sit.load_teacher(ctx.model_dir, ctx.device)
    config = teacher.config
    n_layers = int(config.num_hidden_layers)
    scaling = teacher_scaling(config)
    ispec = sit.IndexerSpec(d_model=int(config.hidden_size))
    load_started = time.perf_counter()
    eval_params = load_eval_params(ctx, spec, n_layers)
    load_s = time.perf_counter() - load_started  # inside startup_s; the budget prices it apart
    names = rt.selector_names(spec.seeds, with_indexers=spec.with_indexers)
    prompts = {p["prompt_id"]: p for p in ctx.stage.meta["prompts"]}
    out_dir = ctx.ckpt_dir / "eval" / spec.stage
    out_dir.mkdir(parents=True, exist_ok=True)
    startup_s = time.time() - spawned_at if spawned_at is not None else None
    unit_times: list[dict[str, Any]] = []
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
            rt._ack_signal(ctx, {"phase": f"eval-{spec.stage}", "completed_prompts": done})
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
            options, option_bytes, answer = ctx.stage.options(prompt) if do_mc else ([], [], -1)
            started = time.perf_counter()
            output = evaluate_unit(
                teacher, tokens, q0, q1, n0, n1, do_select=do_select, do_mc=do_mc,
                options=options, option_bytes=option_bytes, answer=answer,
                eval_params=eval_params, n_selectors=len(names), profile=profile,
                scaling=scaling, ispec=ispec, device=ctx.device)
            _sync(ctx.device)
            unit_times.append({"unit": unit["unit"], "select": do_select, "mc": do_mc,
                               "rows": q1 - q0, "seconds": time.perf_counter() - started})
            recall[row] = output.recall
            ties[row] = output.ties
            max_selected[row] = output.max_selected
            mc[row] = output.mc_scores
            correct[row] = output.mc_correct
        payload = {"unit_ids": np.asarray(chunk_ids), "recall": recall, "ties": ties,
                   "max_selected_tokens": max_selected, "mc_scores": mc, "mc_correct": correct,
                   "selectors": np.asarray(names)}
        buffer_path = out_dir / f".chunk-{chunk_name}.tmp-{os.getpid()}.npz"
        np.savez(buffer_path, **payload)
        with buffer_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(buffer_path, target_path)
        done += len(chunk_ids)
    return {"worker": ctx.worker, "stage": spec.stage, "prompts": done, "engine": ENGINE,
            "timings": {"startup_s": startup_s, "load_s": load_s, "units": unit_times}}


def unit_kind(record: Mapping[str, Any]) -> str:
    if record["select"] and record["mc"]:
        return "select_mc"
    return "select_only" if record["select"] else "mc_only"


def summarise_units(records: Sequence[Mapping[str, Any]], skip: int) -> dict[str, Any]:
    """Per kind: mean seconds over units after the first ``skip`` of that kind, and the
    mean query rows of the measured selection units."""

    by_kind: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_kind.setdefault(unit_kind(record), []).append(record)
    out: dict[str, Any] = {}
    rows: list[int] = []
    for kind, items in sorted(by_kind.items()):
        kept = items[skip:]
        out[kind] = {"units": len(items), "measured": len(kept),
                     "mean_s": float(np.mean([r["seconds"] for r in kept])) if kept else None,
                     "mean_rows": float(np.mean([r["rows"] for r in kept])) if kept else None}
        if kind != "mc_only":
            rows.extend(int(r["rows"]) for r in kept)
    out["selection_mean_rows"] = float(np.mean(rows)) if rows else None
    return out


__all__ = [
    "ENGINE",
    "UnitOutput",
    "WorkerBanks",
    "add_sequence_kl",
    "config_digest",
    "devkl_sequence",
    "eval_keys",
    "evaluate_unit",
    "load_eval_params",
    "mean_sequence_kl",
    "run_devkl_worker",
    "run_eval_worker",
    "run_training_worker",
    "steady_mean",
    "summarise_steps",
    "summarise_units",
    "teacher_scaling",
    "train_step",
    "unit_kind",
]
