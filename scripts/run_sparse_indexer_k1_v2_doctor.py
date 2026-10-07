#!/usr/bin/env python3
"""CPU doctor of the K1 successor screen (q3-k1-localization-screen-v2).

v1's K1 doctor (``scripts/run_sparse_indexer_k1_doctor.py``) keeps covering
the objects v2 shares with v1 (capture path, targets, statistics, data). This
doctor covers what v2 changes, each case against v1's own code:

* ``bank_equivalence``: the batched bank against v1's per-indexer path in
  float64 (loss, every gradient before clipping, the per-indexer clip norm,
  the parameters after one Adam step, and the Adam step bit for bit on
  identical clipped gradients), at a small shape with several row chunks and at
  the registered indexer shape;
* ``slot_independence``: changing one indexer leaves every other indexer's
  loss and gradients bit-identical;
* ``selection_equivalence``: the composite-key top-k selection and the shared
  U/U_k top-k against v1's selection, tie and union functions, exactly,
  including exact ties and signed zeros;
* ``eval_unit_vs_v1``: one evaluation unit on a tiny random Qwen3 model
  against v1's per-layer, per-selector evaluation loop;
* ``end_to_end``: the v2 entry point on the tiny model and a synthetic bundle
  built by the real builder: a digest mismatch exits 2; the smoke (its gate on
  the main job and the extension, and SMOKE_PASS_OVER_BUDGET under tight
  limits); headroom-dev; the three resume legs with a real SIGUSR1 and a stale
  marker, compared bit for bit by v1's comparison script; a SIGUSR1 while
  workers start; 0a-k1, its continuation after the LR freeze, a corrupt final
  generation (exit 3), and the extension (refused for a read that does not call
  for it; otherwise only the V1-failing target is retrained and re-read).

Every number is a synthetic-case number. A PASS proves executability and
equivalence only; it says nothing about Qwen3-0.6B-Base, the data or the claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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

from harness.sparse_indexer_k1_marker import read_checkpoint_marker  # noqa: E402
from scripts.run_sparse_indexer_k1_doctor import (  # noqa: E402
    TinyRun,
    build_tiny_bundle,
    copy_checkpoints,
    final_state,
    make_tiny_model,
    receipt_of,
    rewrite_main_read,
    signal_during_worker_start,
    write_stand_in_receipt,
)

DOCTOR_NAME = "q3-k1-localization-screen-v2-cpu-doctor"
EVIDENCE_GRADE = (
    "EXECUTABILITY_AND_EQUIVALENCE_ONLY: float64 and exact comparisons with v1's per-indexer "
    "code, a tiny randomly initialised Qwen3 model, a byte-level stand-in tokenizer and a "
    "synthetic bundle built by the real builder code. Nothing here touches Qwen3-0.6B-Base, "
    "Belebele, FineWeb or ParaDocs."
)
ENTRY = PROJECT_ROOT / "scripts" / "run_sparse_indexer_phase0a_v2.py"
CONTRACT = (PROJECT_ROOT / "experiments" / "architectures"
            / "translation-supervised-sparse-indexer-k1-screen-v2.yaml")
EXPERIMENT_ID = "q3-k1-localization-screen-v2"
FLOAT64_TOLERANCE = {"loss": 1e-12, "clip_norm": 1e-12, "grad": 1e-11, "param": 1e-11}
PROVENANCE = ("harness/sparse_indexer_bank.py", "harness/sparse_indexer_k1_runtime_v2.py",
              "harness/sparse_indexer_k1_budget_v2.py", "scripts/run_sparse_indexer_phase0a_v2.py",
              "scripts/run_sparse_indexer_k1_v2_doctor.py", "harness/sparse_indexer_torch.py",
              "harness/sparse_indexer_k1_runtime.py", "scripts/run_sparse_indexer_phase0a.py")


# --------------------------------------------------------------------------- #
# Fixtures shared with the tests
# --------------------------------------------------------------------------- #


def freeze_stand_in(root: Path, experiment_id: str = EXPERIMENT_ID) -> tuple[Path, str, Path]:
    from scripts import preregister

    prereg = root / "program" / "preregistrations" / f"{experiment_id}.md"
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text("# doctor stand-in preregistration\n\nSynthetic only.\n",
                      encoding="utf-8")
    ledger = root / "program" / "preregistrations" / "ledger.jsonl"
    preregister.freeze(prereg, experiment_id, ledger=ledger, root=root)
    return prereg, preregister.sha256_file(prereg), ledger


class TinyRunV2(TinyRun):
    """v1's tiny-run fixture pointed at the v2 entry point, contract and id."""

    def __init__(self, root: Path) -> None:  # noqa: D107 - v1's fields
        self.root = root
        self.model = make_tiny_model(root / "model")
        self.bundle, self.bundle_sha = build_tiny_bundle(root)
        self.prereg, self.prereg_sha, self.ledger = freeze_stand_in(root / "repo")
        self.receipt = root / "receipt.json"
        self.receipt_sha = write_stand_in_receipt(self.receipt)

    def argv(self, phase: str, run_dir: Path, *extra: str, bundle_sha: str | None = None,
             workers: int = 2) -> list[str]:
        argv = super().argv(phase, run_dir, *extra, bundle_sha=bundle_sha, workers=workers)
        argv[1], argv[2] = str(ENTRY), str(CONTRACT)
        return argv


def tight_limits(path: Path, minutes: int = 5) -> Path:
    """A limits table that no real projection fits (the over-budget smoke case)."""

    from harness import sparse_indexer_k1_budget_v2 as budget

    table = {job: {"minutes": minutes, "max_gpu_hours": budget.gpu_hours(gpus, minutes)}
             for job, gpus in budget.JOBS}
    path.write_text(json.dumps(table), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #


def _random_targets(length: int, seed: int) -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_torch as sit

    generator = torch.Generator().manual_seed(seed)
    logits = torch.randn(3, length, length, generator=generator, dtype=torch.float64) * 3.0
    future = torch.arange(length)[None, :] > torch.arange(length)[:, None]
    probs = torch.softmax(logits.masked_fill(future[None], float("-inf")), dim=-1)
    return sit.block_targets(probs, torch.arange(length))


def registered_keys() -> list[str]:
    from harness import sparse_indexer_k1_runtime as rt

    return [rt.indexer_key(t, lr, s) for t in ("hs", "mp") for lr in rt.LEARNING_RATES
            for s in (42, 43, 44)]


def case_bank_equivalence() -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_torch as sit

    small = sit.IndexerSpec(d_model=32, heads=2, dim=16, rope_dims=16)
    settings = {"small-3-chunks": (small, 67, 16, 1), "small-batch-2": (small, 67, 1024, 2),
                "registered-shape": (sit.IndexerSpec(), 41, 16, 1)}
    gates: dict[str, bool] = {}
    details: dict[str, Any] = {}
    for name, (spec, length, chunk, sequences) in settings.items():
        generator = torch.Generator().manual_seed(11)
        hidden = torch.randn(length, spec.d_model, generator=generator, dtype=torch.float64)
        report = skb.compare_with_v1(spec, 3, registered_keys(), hidden,
                                     _random_targets(length, 0), device="cpu",
                                     dtype=torch.float64, row_chunk=chunk, sequences=sequences)
        details[name] = report
        gates[f"{name}:loss"] = report["loss_max_rel"] < FLOAT64_TOLERANCE["loss"]
        gates[f"{name}:clip_norm"] = report["clip_norm_max_rel"] < FLOAT64_TOLERANCE["clip_norm"]
        gates[f"{name}:gradients"] = (max(report["grad_max_rel_fro"].values())
                                      < FLOAT64_TOLERANCE["grad"])
        gates[f"{name}:params_after_step"] = (max(report["param_after_step_max_rel_fro"].values())
                                              < FLOAT64_TOLERANCE["param"])
        gates[f"{name}:adam_bitwise"] = report["adam_step_bitwise"] is True
    bank = skb.LayerBank(small, 5, registered_keys(), "cpu")
    exact = True
    for cell, leaves in zip(bank.cells, bank.leaves, strict=True):
        for slot, seed in enumerate(cell.seeds):
            reference = dict(sit.BlockIndexer.initialised(small, seed, 5, cell.target)
                             .named_parameters())
            exact &= all(torch.equal(leaves[n][slot].detach(), reference[n].detach())
                         for n in skb.PARAM_NAMES)
    gates["initialisation_bitwise"] = bool(exact)
    return {"gates": gates, "details": details, "tolerance": FLOAT64_TOLERANCE}


def case_slot_independence() -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_torch as sit

    spec = sit.IndexerSpec(d_model=32, heads=2, dim=16, rope_dims=16)
    length = 37
    generator = torch.Generator().manual_seed(3)
    hidden = torch.randn(length, spec.d_model, generator=generator, dtype=torch.float64)
    targets = _random_targets(length, 1)

    def provide(first: int, end: int) -> dict[str, Any]:
        return {k: targets[k][first:end, : end // 4] for k in ("hs", "mp", "valid")}

    def run(perturb: bool) -> tuple[Any, dict[str, Any], Any]:
        bank = skb.LayerBank(spec, 1, registered_keys(), "cpu", dtype=torch.float64)
        params = bank.working_params()
        if perturb:
            with torch.no_grad():
                params["wq"][4] += 0.5
                params["gate_b"][4] -= 2.0
        kl = bank.accumulate_sequence(params, hidden, provide, grad_scale=1.0, row_chunk=8)
        bank.adopt_grads(params)
        norms = bank.clip_()
        return kl, {n: params[n].grad.clone() for n in skb.PARAM_NAMES}, norms

    base_kl, base, base_norms = run(False)
    moved_kl, moved, moved_norms = run(True)
    others = [i for i in range(18) if i != 4]
    return {"gates": {
        "other_losses_bitwise": bool(torch.equal(base_kl[others], moved_kl[others])),
        "perturbed_loss_moves": bool(base_kl[4] != moved_kl[4]),
        "other_gradients_bitwise": all(bool(torch.equal(base[n][others], moved[n][others]))
                                       for n in skb.PARAM_NAMES),
        "other_clip_norms_bitwise": bool(torch.equal(base_norms[others], moved_norms[others])),
    }}


def case_selection_equivalence() -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_torch as sit

    mismatches: list[str] = []
    cases = 0
    for trial, k in enumerate([5, 12, 39, 40, 64, 1, 256, 3]):
        generator = torch.Generator().manual_seed(100 + trial)
        n_rows, n_blocks = 9, 40
        rows = torch.arange(n_blocks * 4 - n_rows, n_blocks * 4) - (trial % 3) * 7
        valid = sit.complete_block_mask(rows, n_blocks)
        raw = torch.randn(5, n_rows, n_blocks, generator=generator)
        raw[0] = (raw[0] * 2).round() / 2
        raw[1] = torch.where(raw[1] > 0, torch.zeros_like(raw[1]), -torch.zeros_like(raw[1]))
        raw[2] = torch.relu(raw[2]) * torch.sign(torch.randn(n_rows, n_blocks,
                                                             generator=generator))
        result = skb.select_blocks(raw[None], valid, rows, 37, 61, k)
        for s in range(raw.shape[0]):
            cases += 1
            chosen = sit.select_top_blocks(raw[s], valid, k)
            hits = (sit.block_selection_recall(chosen, rows, 37, 61) * 24).round().long()
            selected = int(((chosen >= 0).sum(dim=-1) * 4 + (rows + 1) % 4).max())
            if not (torch.equal(result.hits[0, s], hits)
                    and int(result.ties[0, s]) == sit.boundary_ties(raw[s], valid, k)
                    and int(result.selected_max[0, s]) == selected):
                mismatches.append(f"block trial {trial} selector {s}")
    for trial in range(6):
        generator = torch.Generator().manual_seed(200 + trial)
        length = 90
        rows = torch.arange(length - 7, length) - trial * 8
        logits = torch.randn(4, rows.numel(), length, generator=generator) * 6.0
        if trial % 2:
            logits = (logits * 0.5).round() * 40.0
        future = torch.arange(length)[None, :] > rows[:, None]
        probs = torch.softmax(logits.masked_fill(future[None], float("-inf")), dim=-1)
        for k_values in ((16, 3), (500, 64)):
            values = skb.union_hits(probs, rows, k_values, 3, 40)
            for value, k in zip(values, k_values, strict=True):
                cases += 1
                reference = (sit.union_topk_recall(probs, rows, k, 3, 40) * 37).round().long()
                if not torch.equal(value, reference):
                    mismatches.append(f"union trial {trial} k {k}")
    return {"gates": {"exactly_equal_to_v1": not mismatches},
            "details": {"cases": cases, "mismatches": mismatches}}


def v1_unit_reference(teacher: Any, tokens: np.ndarray, q0: int, q1: int, n0: int, n1: int,
                      seeds: list[int], profile: Any, scaling: float, spec: Any
                      ) -> tuple[np.ndarray, np.ndarray, int]:
    """v1's ``run_eval_worker`` selection loop for one unit (initialised indexers)."""

    import torch

    from harness import sparse_indexer_k1_runtime as rt
    from harness import sparse_indexer_torch as sit

    n_layers = int(teacher.config.num_hidden_layers)
    names = rt.selector_names(seeds)
    recall = np.full((n_layers, len(names)), np.nan, dtype=np.float32)
    ties = np.zeros(len(names), dtype=np.int32)
    max_selected = 0
    ids = torch.as_tensor(tokens.astype(np.int64))[None]
    rows = torch.arange(q0, q1)
    with sit.CaptureSession(teacher, range(n_layers), query_rows=rows) as cap, torch.no_grad():
        teacher(input_ids=ids, use_cache=False, logits_to_keep=1)
        for layer in range(n_layers):
            q, k, hidden = cap.query[layer][0], cap.key[layer][0], cap.hidden[layer][0]
            probs = sit.head_probs_rows(q, k, rows, scaling)
            dense = sit.block_targets(probs, rows, include_hm=True)
            valid = dense["valid"]
            for col, name in enumerate(names):
                if name.startswith("T:") or name.startswith("I:"):
                    if name.startswith("T:"):
                        score = dense[name[2:]]
                    else:
                        _, target, seed = name.split(":")
                        indexer = sit.BlockIndexer.initialised(spec, int(seed), layer, target)
                        score, valid = indexer(hidden, rows)
                    chosen = sit.select_top_blocks(score, valid, profile.k_blocks)
                    ties[col] += sit.boundary_ties(score, valid, profile.k_blocks)
                    values = sit.block_selection_recall(chosen, rows, n0, n1)
                    selected = (chosen >= 0).sum(dim=-1) * 4 + (rows + 1) % 4
                    max_selected = max(max_selected, int(selected.max()))
                elif name == "U":
                    values = sit.union_topk_recall(probs, rows, profile.union_k, n0, n1)
                elif name == "Uk":
                    values = sit.union_topk_recall(probs, rows, profile.union_budget_k, n0, n1)
                else:
                    values = sit.random_block_recall(rows, n0, n1, profile.k_blocks)
                recall[layer, col] = float(values.mean()) * 100.0
    return recall, ties, max_selected


def case_eval_unit_vs_v1(tmp: Path) -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_k1_runtime as rt
    from harness import sparse_indexer_k1_runtime_v2 as rt2
    from harness import sparse_indexer_torch as sit

    model_dir = make_tiny_model(tmp / "unit-model")
    sit.set_determinism(allow_tf32=True)
    teacher = sit.load_teacher(model_dir, "cpu")
    scaling = rt2.teacher_scaling(teacher.config)
    spec = sit.IndexerSpec(d_model=int(teacher.config.hidden_size))
    profile = rt.Profile.tiny()
    seeds = [42, 43, 44]
    keys = [f"{t}|1e-3|{s}" for t in sit.TRAINED_TARGETS for s in seeds]
    n_layers = int(teacher.config.num_hidden_layers)
    params = {layer: skb.stack_from_state(skb.initial_state(spec, layer, keys), layer, keys,
                                          "cpu") for layer in range(n_layers)}
    rng = np.random.default_rng(4)
    worst: dict[str, float] = {"dense": 0.0, "indexer": 0.0}
    tie_equal, selected_equal = True, True
    for unit in range(4):
        length = 120 + 3 * unit
        tokens = rng.integers(2, 500, size=length + 6).astype(np.int64)
        q0, q1, n0, n1 = length, length + 6, 20 + unit, 60 + 2 * unit
        output = rt2.evaluate_unit(teacher, tokens, q0, q1, n0, n1, do_select=True,
                                   do_mc=False, eval_params=params, n_selectors=12,
                                   profile=profile, scaling=scaling, ispec=spec,
                                   device=torch.device("cpu"))
        recall, ties, selected = v1_unit_reference(teacher, tokens, q0, q1, n0, n1, seeds,
                                                   profile, scaling, spec)
        dense_cols = list(range(6))
        worst["dense"] = max(worst["dense"], float(np.abs(output.recall[:, dense_cols]
                                                          - recall[:, dense_cols]).max()))
        worst["indexer"] = max(worst["indexer"], float(np.abs(output.recall[:, 6:]
                                                            - recall[:, 6:]).max()))
        tie_equal &= bool(np.array_equal(output.ties, ties))
        selected_equal &= output.max_selected == selected
    return {"gates": {"dense_selectors_match": worst["dense"] <= 1e-4,
                      "indexer_selectors_match": worst["indexer"] <= 1e-4,
                      "tie_counts_equal": tie_equal, "max_selected_equal": selected_equal},
            "details": {"max_abs_recall_difference_points": worst}}


def case_end_to_end(tmp: Path) -> dict[str, Any]:
    from scripts.compare_sparse_indexer_resume import compare

    run = TinyRunV2(tmp / "e2e")
    gates: dict[str, bool] = {}
    details: dict[str, Any] = {}
    bad = run.run("smoke", tmp / "bad-digest", bundle_sha="0" * 64)
    gates["digest_mismatch_exits_2"] = bad.returncode == 2
    smoke = run.run("smoke", tmp / "smoke", workers=1)
    smoke_receipt = receipt_of(tmp / "smoke") if smoke.returncode == 0 else {}
    projection = smoke_receipt.get("projection", {})
    gates["smoke_passes"] = smoke_receipt.get("status") == "SMOKE_PASS"
    gates["smoke_gates_main_and_extension"] = all(
        "required_limit_minutes" in projection.get(job, {}) for job in ("main", "extension"))
    gates["smoke_measures_every_rate"] = bool(projection.get("rates"))
    details["smoke_stderr_tail"] = smoke.stderr[-800:] if smoke.returncode else ""
    over = run.run("smoke", tmp / "smoke-over", "--limits-override",
                   str(tight_limits(tmp / "tight-limits.json")), workers=1)
    gates["smoke_over_budget_under_tight_limits"] = over.returncode == 0 and receipt_of(
        tmp / "smoke-over")["status"] == "SMOKE_PASS_OVER_BUDGET"
    headroom = run.run("headroom-dev", tmp / "headroom")
    gates["headroom_dev_completes"] = headroom.returncode == 0 and "decision" in receipt_of(
        tmp / "headroom")
    details["headroom_stderr_tail"] = headroom.stderr[-800:] if headroom.returncode else ""
    r0 = run.run("resume-test", tmp / "r0", "--stop-after-step", "4", "--checkpoint-every", "2")
    r1_dir = tmp / "r1"
    r1_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(run.argv("resume-test", r1_dir, "--stop-after-step", "4",
                                        "--hold-after-step", "2", "--checkpoint-every", "2"),
                               env=run.env(r1_dir), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    holding = r1_dir / "phase-0a-k1" / "checkpoints" / "holding"
    deadline = time.time() + 600
    while time.time() < deadline and len(list(holding.glob("worker-*.json"))) < 2:
        if process.poll() is not None:
            break
        time.sleep(0.5)
    stale = r1_dir / "checkpoint.ready"
    stale.write_text("stale marker from a periodic checkpoint\n", encoding="utf-8")
    process.send_signal(signal.SIGUSR1)
    _, r1_err = process.communicate(timeout=600)
    marker = read_checkpoint_marker(stale) if stale.is_file() else {"acks": {}}
    gates["signal_save_exits_75"] = process.returncode == 75
    gates["stale_marker_replaced_after_acks"] = (
        marker.get("trigger") == "SIGUSR1" and len(marker["acks"]) == 2
        and {a.get("step") for a in marker["acks"].values()} == {2})
    r2_dir = tmp / "r2"
    (r2_dir / "phase-0a-k1").mkdir(parents=True, exist_ok=True)
    shutil.copytree(r1_dir / "phase-0a-k1" / "checkpoints",
                    r2_dir / "phase-0a-k1" / "checkpoints")
    r2 = run.run("resume-test", r2_dir, "--stop-after-step", "4", "--checkpoint-every", "2")
    (r1_dir / "termination.env").write_text(
        "reason=signal_USR1_checkpoint_confirmed\nexit_code=75\ncheckpoint_ready=true\n",
        encoding="utf-8")
    if r0.returncode == 0 and r2.returncode == 0:
        comparison = compare(tmp / "r0", r1_dir, r2_dir)
        gates["resume_bitwise_equal"] = comparison["equivalent"]
        details["resume"] = {"checks": comparison["checks"],
                             "r2_resumed_from": comparison["r2_resumed_from"]}
    else:
        gates["resume_bitwise_equal"] = False
        details["resume_stderr"] = (r0.stderr[-600:], r1_err[-600:], r2.stderr[-600:])
    early = signal_during_worker_start(run, tmp / "early-signal")
    _, early_err = early.communicate(timeout=600)
    early_marker = tmp / "early-signal" / "checkpoint.ready"
    gates["signal_during_worker_start_checkpoints"] = (
        early.returncode == 75 and early_marker.is_file()
        and read_checkpoint_marker(early_marker).get("trigger") == "SIGUSR1")
    details["early_signal_stderr_tail"] = early_err[-800:] if early.returncode != 75 else ""
    main_run = run.run("0a-k1", tmp / "main")
    gates["main_completes_with_verdict"] = main_run.returncode == 0 and receipt_of(
        tmp / "main")["verdict"]["verdict"] in {
        "GO", "NEGATIVE", "INCONCLUSIVE", "UNINTERPRETABLE", "HOLD", "V1_EXTENSION_REQUIRED"}
    names = ("lr_freeze_hashed_before_audit", "main_read_persisted",
             "main_continues_after_freeze", "corrupt_final_generation_fails_closed",
             "extension_refused_without_v1_failure", "extension_rereads_only_failing_target",
             "extension_keeps_untrained_indexers_bitwise")
    if main_run.returncode != 0:
        details["main_stderr_tail"] = main_run.stderr[-1500:]
        gates.update(dict.fromkeys(names, False))
        return {"gates": gates, "details": details}
    main_receipt = receipt_of(tmp / "main")
    main_ckpt = tmp / "main" / "phase-0a-k1" / "checkpoints"
    details["main"] = {"verdict": main_receipt["verdict"]["verdict"],
                       "lr_freeze": main_receipt["lr_freeze"]["selected_lr"],
                       "units": main_receipt["units"]}
    gates["lr_freeze_hashed_before_audit"] = bool(main_receipt["hashes"].get("lr_freeze_sha256"))
    gates["main_read_persisted"] = (main_ckpt / "main-read.json").is_file() and (
        hashlib.sha256((main_ckpt / "main-read.json").read_bytes()).hexdigest()
        == main_receipt["hashes"].get("main_read_sha256"))
    resumed_ckpt = copy_checkpoints(tmp / "main", tmp / "main-continued", "main-read.json")
    chunks = sorted((resumed_ckpt / "eval" / "audit-main").glob("chunk-*.npz"))
    for chunk in chunks[: len(chunks) // 2]:
        chunk.unlink()
    continued = run.run("0a-k1", tmp / "main-continued")
    if continued.returncode == 0:
        again = receipt_of(tmp / "main-continued")
        gates["main_continues_after_freeze"] = (
            again["verdict"]["verdict"] == main_receipt["verdict"]["verdict"]
            and again["lr_freeze"] == main_receipt["lr_freeze"]
            and again["training_workers"] == []
            and all(again["targets"][t]["xi"] == main_receipt["targets"][t]["xi"]
                    for t in ("hs", "mp")))
    else:
        gates["main_continues_after_freeze"] = False
        details["main_continued_stderr_tail"] = continued.stderr[-1500:]
    corrupt_ckpt = copy_checkpoints(tmp / "main", tmp / "main-corrupt", "eval", "lr_freeze.json",
                                    "main-read.json")
    final = sorted((corrupt_ckpt / "worker-0").glob("step-*"))[-1] / "state.safetensors"
    data = bytearray(final.read_bytes())
    data[-1] ^= 0xFF
    final.write_bytes(bytes(data))
    corrupt = run.run("0a-k1", tmp / "main-corrupt")
    gates["corrupt_final_generation_fails_closed"] = corrupt.returncode == 3 and (
        "fails its digest check" in corrupt.stderr)
    refused_dir = tmp / "extension-refused"
    rewrite_main_read(copy_checkpoints(tmp / "main", refused_dir, "eval") / "main-read.json",
                      mp_region="go")
    refused = run.run("0a-k1-extend", refused_dir)
    gates["extension_refused_without_v1_failure"] = refused.returncode == 3 and not (
        refused_dir / "phase-0a-k1" / "receipt-extension.json").exists()
    ext_dir = tmp / "extension"
    synthetic = rewrite_main_read(
        copy_checkpoints(tmp / "main", ext_dir, "eval") / "main-read.json", mp_region="none")
    extension = run.run("0a-k1-extend", ext_dir)
    if extension.returncode == 0:
        ext_receipt = receipt_of(ext_dir, "receipt-extension.json")
        steps = main_receipt["training_workers"][0]["final_step"]
        hs_lr = main_receipt["lr_freeze"]["selected_lr"]["hs"]
        changed: set[str] = set()
        untouched = True
        for worker in (0, 1):
            before, after = final_state(tmp / "main", worker, steps), final_state(
                ext_dir, worker, 3 * steps)
            for name in before:
                same = np.array_equal(before[name].numpy(), after[name].numpy())
                if f"|hs|{hs_lr}|" in name:
                    if "|param|" in name and not same:
                        changed.add(name)
                elif not same:
                    untouched = False  # any other indexer's parameter or Adam state moved
        gates["extension_rereads_only_failing_target"] = (
            synthetic["extension_targets"] == ["hs"]
            and ext_receipt["reread_targets"] == ["hs"]
            and ext_receipt["kept_main_read_targets"] == ["mp"]
            and set(ext_receipt["targets"]) == {"hs"} and bool(changed))
        gates["extension_keeps_untrained_indexers_bitwise"] = untouched
        details["extension"] = {"verdict": ext_receipt["verdict"]["verdict"],
                                "final_verdict": ext_receipt["final_verdict"]["verdict"],
                                "changed_parameters": len(changed)}
    else:
        gates["extension_rereads_only_failing_target"] = False
        gates["extension_keeps_untrained_indexers_bitwise"] = False
        details["extension_stderr_tail"] = extension.stderr[-1500:]
    return {"gates": gates, "details": details}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-end-to-end", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists():
        raise SystemExit(f"{args.output} exists; a doctor rerun writes a new path")
    started = time.perf_counter()
    cases: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="k1-v2-doctor-") as raw:
        tmp = Path(raw)
        cases["bank_equivalence"] = case_bank_equivalence()
        cases["slot_independence"] = case_slot_independence()
        cases["selection_equivalence"] = case_selection_equivalence()
        cases["eval_unit_vs_v1"] = case_eval_unit_vs_v1(tmp)
        if not args.skip_end_to_end:
            cases["end_to_end"] = case_end_to_end(tmp)
    case_status = {name: "PASS" if all(case["gates"].values()) else "FAIL"
                   for name, case in cases.items()}
    all_pass = all(status == "PASS" for status in case_status.values())
    payload = {
        "schema_version": "1.0", "doctor": DOCTOR_NAME,
        "status": "K1_V2_DOCTOR_PASS" if all_pass else "K1_V2_DOCTOR_FAIL",
        "evidence_grade": EVIDENCE_GRADE, "numbers_are_synthetic": True,
        "case_status": case_status, "cases": cases,
        "runtime_seconds": time.perf_counter() - started,
        "provenance": {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
                       for name in PROVENANCE},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({"status": payload["status"], "case_status": case_status}))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
