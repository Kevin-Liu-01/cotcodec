#!/usr/bin/env python3
"""g2b-state-dtype-v1 (EXPLORATORY): teacher-force both arms' rollouts through the trainer path.

Runs inside the research overlay (torch 2.11, transformers 5.15, flash-linear-attention 0.5.2;
no flash_attn, no causal_conv1d) on the docker-research lane. Input: the merged tf-input.json of
one model's two rollout arms (fp32 and bf16 GDN state), hash-bound as the study artifact.

Paths (the G2 pilot's r1 and r4, plus the packed trainer path):

* ``r1``: HF transformers bf16, one unpacked sequence per forward, SDPA (flash or efficient),
  FLA ``chunk_gated_delta_rule`` for the gated delta rule (the stock resolution in 5.15).
* ``r2``: the packed varlen path RL trainers such as verl use: several sequences concatenated
  into one row with per-sequence position ids, FLA ``chunk_gated_delta_rule`` with
  ``cu_seqlens`` (HF 5.15 forwards ``cu_seq_lens_q`` to it), the short convolution applied per
  sequence (verl's fallback when causal_conv1d is absent; HF's torch fallback would mix
  sequences), and varlen attention (torch.nn.attention.varlen.varlen_attn, else per-segment
  SDPA). All dense layers see the packed row, as in training.
* ``r4``: the fp32 reference: fp32 weights, TF32 off, memory-efficient SDPA, HF's torch-native
  chunked gated delta rule in fp32.

The trainer's GDN state (FLA 0.5.2, fla/ops/common/chunk_delta_h.py): the running state is an
fp32 accumulator inside the kernel (lines 90-104), each 64-token chunk's state is stored in the
input dtype for the output kernel (``h = k.new_empty``, lines 703/706: bf16), and the final state
is fp32 (lines 704/707, not requested here). The job also records a runtime probe of this.

Subcommands: ``plan``, ``selftest`` (CPU, tiny random models), ``run``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as g2  # noqa: E402
from harness import g2b_state_dtype as gb  # noqa: E402
from scripts import run_g2_teacher_force as base  # noqa: E402

PATHS = ("r1", "r2", "r4")
GDN_IMPL = {"r1": "fla_chunk", "r2": "fla_chunk", "r4": "torch_chunk_fp32"}
ATTN_NAME = "g2b_varlen"
#: Packed-attention state: the current pack's sequence bounds and the kernel to use.
VARLEN: dict[str, Any] = {"bounds": None, "backend": "sdpa-segments", "calls": 0}


# --------------------------------------------------------------------------- GDN switch


class GdnSwitch(base.GdnSwitch):
    """The pilot's switch, plus packed calls: FLA kernels get ``cu_seqlens``; the torch
    reference, which has no varlen form, runs once per sequence (verl's fallback)."""

    packed_calls = 0

    def use(self, impl: str, segment_torch: bool = True) -> None:
        import torch

        if impl == "torch_chunk_fp32":
            fn = self.torch_chunk
        else:
            from fla.ops.gated_delta_rule import (
                chunk_gated_delta_rule,
                fused_recurrent_gated_delta_rule,
            )

            fn = chunk_gated_delta_rule if impl == "fla_chunk" else fused_recurrent_gated_delta_rule
        switch = self

        def gated_delta_rule(
            query: Any,
            key: Any,
            value: Any,
            g: Any = None,
            beta: Any = None,
            initial_state: Any = None,
            output_final_state: bool = False,
            use_qk_l2norm_in_kernel: bool = False,
            cu_seqlens: Any = None,
            **_ignored: Any,
        ) -> Any:
            switch.calls += 1
            kwargs = {
                "g": g,
                "beta": beta,
                "initial_state": initial_state,
                "output_final_state": output_final_state,
                "use_qk_l2norm_in_kernel": use_qk_l2norm_in_kernel,
            }
            if cu_seqlens is None:
                return fn(query, key, value, **kwargs)
            switch.packed_calls += 1
            if impl != "torch_chunk_fp32":
                return fn(query, key, value, cu_seqlens=cu_seqlens, **kwargs)
            if not segment_torch:  # selftest only: the leak a naive packed forward would have
                return fn(query, key, value, **kwargs)
            bounds = [int(x) for x in cu_seqlens.tolist()]
            outs = []
            for start, end in zip(bounds[:-1], bounds[1:], strict=True):
                part = dict(kwargs, g=g[:, start:end], beta=beta[:, start:end])
                out, _ = fn(query[:, start:end], key[:, start:end], value[:, start:end], **part)
                outs.append(out)
            return torch.cat(outs, dim=1), None

        self.module.torch_chunk_gated_delta_rule = gated_delta_rule
        self.impl = impl
        self.calls = 0
        self.packed_calls = 0


# --------------------------------------------------------------------------- packed attention


def segments(bounds: list[int]) -> list[tuple[int, int]]:
    return list(zip(bounds[:-1], bounds[1:], strict=True))


def varlen_attention(
    module: Any,
    query: Any,
    key: Any,
    value: Any,
    attention_mask: Any,
    dropout: float = 0.0,
    scaling: float | None = None,
    **_kwargs: Any,
) -> tuple[Any, None]:
    """Causal attention within each packed sequence. query [1, H, T, D], key/value
    [1, Hkv, T, D]; returns [1, T, H, D] like HF's SDPA integration."""

    import torch
    import torch.nn.functional as F

    bounds = VARLEN["bounds"]
    if bounds is None or query.shape[0] != 1 or query.shape[2] != bounds[-1]:
        raise RuntimeError("packed attention called outside a pack")
    VARLEN["calls"] += 1
    n_rep = query.shape[1] // key.shape[1]
    if n_rep > 1:
        key = key.repeat_interleave(n_rep, dim=1)
        value = value.repeat_interleave(n_rep, dim=1)
    q = query[0].transpose(0, 1).contiguous()
    k = key[0].transpose(0, 1).contiguous()
    v = value[0].transpose(0, 1).contiguous()
    if VARLEN["backend"] == "torch-varlen":
        from torch.nn.attention.varlen import varlen_attn

        cu = torch.tensor(bounds, dtype=torch.int32, device=q.device)
        longest = max(end - start for start, end in segments(bounds))
        out = varlen_attn(q, k, v, cu, cu, longest, longest, scale=scaling, window_size=(-1, 0))
    else:
        outs = []
        for start, end in segments(bounds):
            o = F.scaled_dot_product_attention(
                q[start:end].transpose(0, 1)[None],
                k[start:end].transpose(0, 1)[None],
                v[start:end].transpose(0, 1)[None],
                is_causal=True,
                scale=scaling,
            )
            outs.append(o[0].transpose(0, 1))
        out = torch.cat(outs, dim=0)
    return out[None], None


def register_attention() -> None:
    from transformers import AttentionInterface

    AttentionInterface.register(ATTN_NAME, varlen_attention)


def attention_configs(model: Any) -> list[Any]:
    configs: dict[int, Any] = {}
    for module in model.modules():
        if hasattr(module, "q_proj") and hasattr(module, "config") and hasattr(module, "o_proj"):
            configs[id(module.config)] = module.config
    return list(configs.values())


@contextlib.contextmanager
def packed_mode(model: Any, bounds: list[int], segment_conv: bool = True) -> Any:
    """Within: the packed attention implementation, and the convolution applied per sequence."""

    import torch
    import transformers.models.qwen3_5.modeling_qwen3_5 as mq

    stock_conv = mq.causal_conv1d_fn
    counters = {"conv_segmented": 0}

    def segmented_conv(
        hidden_states: Any, weight: Any, bias: Any = None, activation: Any = None, **kwargs: Any
    ) -> Any:
        if not segment_conv or hidden_states.shape[-1] != bounds[-1]:
            return stock_conv(hidden_states, weight, bias, activation, **kwargs)
        counters["conv_segmented"] += 1
        outs = [
            stock_conv(hidden_states[:, :, s:e], weight, bias, activation)
            for s, e in segments(bounds)
        ]
        return torch.cat(outs, dim=-1)

    configs = attention_configs(model)
    previous = [c._attn_implementation for c in configs]
    mq.causal_conv1d_fn = segmented_conv
    VARLEN["bounds"] = bounds
    try:
        for c in configs:
            c._attn_implementation_internal = ATTN_NAME
            if c._attn_implementation != ATTN_NAME:
                raise RuntimeError("could not set the packed attention implementation")
        yield counters
    finally:
        mq.causal_conv1d_fn = stock_conv
        VARLEN["bounds"] = None
        for c, old in zip(configs, previous, strict=True):
            c._attn_implementation_internal = old


def text_model(model: Any) -> Any:
    return getattr(model.model, "language_model", model.model)


def head_scores(
    torch: Any, model: Any, hidden: Any, ids: Any, prompt_len: int, chunk: int, device: str
) -> tuple[Any, Any]:
    """Log-prob of each completion token and its distribution's entropy (fp32), as
    run_g2_teacher_force.score_sequence does after the backbone."""

    rows = hidden[prompt_len - 1 : ids.shape[0] - 1]
    target = ids[prompt_len:]
    count = rows.shape[0]
    logp = torch.empty(count, dtype=torch.float32, device=device)
    entropy = torch.empty(count, dtype=torch.float32, device=device)
    for start in range(0, count, chunk):
        end = min(start + chunk, count)
        logits = model.lm_head(rows[start:end]).float()
        log_probs = torch.log_softmax(logits, dim=-1)
        logp[start:end] = log_probs.gather(-1, target[start:end, None])[:, 0]
        entropy[start:end] = -(log_probs.exp() * log_probs).sum(-1)
        del logits, log_probs
    return logp.cpu().numpy(), entropy.cpu().numpy()


def score_pack(
    torch: Any,
    model: Any,
    seqs: list[tuple[list[int], int]],
    chunk: int,
    device: str,
    segment_conv: bool = True,
) -> tuple[list[tuple[Any, Any]], dict[str, int]]:
    """One packed forward over ``seqs`` ((token ids, prompt length) each); per-sequence scores."""

    lengths = [len(ids) for ids, _ in seqs]
    bounds = gb.cu_seqlens(lengths)
    flat = torch.tensor([[t for ids, _ in seqs for t in ids]], dtype=torch.long, device=device)
    position = torch.cat([torch.arange(n, device=device) for n in lengths])[None]
    cu = torch.tensor(bounds, dtype=torch.long, device=device)
    longest = max(lengths)
    with torch.inference_mode(), packed_mode(model, bounds, segment_conv) as counters:
        hidden = text_model(model)(
            input_ids=flat,
            position_ids=position,
            use_cache=False,
            attention_mask={"full_attention": None, "linear_attention": None},
            cu_seq_lens_q=cu,
            cu_seq_lens_k=cu,
            max_length_q=longest,
            max_length_k=longest,
        ).last_hidden_state[0]
        results = []
        for (start, end), (_, prompt_len) in zip(segments(bounds), seqs, strict=True):
            results.append(
                head_scores(
                    torch, model, hidden[start:end], flat[0, start:end], prompt_len, chunk, device
                )
            )
    return results, dict(counters)


# --------------------------------------------------------------------------- runtime checks


def check_varlen_backend(torch: Any) -> dict[str, Any]:
    """torch varlen_attn against per-segment SDPA on random bf16 data; the backend r2 uses."""

    record: dict[str, Any] = {"backend": "sdpa-segments"}
    if not torch.cuda.is_available():
        record["reason"] = "no CUDA"
        return record
    try:
        gen = torch.Generator(device="cuda").manual_seed(42)
        bounds = [0, 700, 1000, 1513]
        q = torch.randn(1, 16, bounds[-1], 256, device="cuda", dtype=torch.bfloat16, generator=gen)
        k = torch.randn(1, 4, bounds[-1], 256, device="cuda", dtype=torch.bfloat16, generator=gen)
        v = torch.randn(1, 4, bounds[-1], 256, device="cuda", dtype=torch.bfloat16, generator=gen)
        VARLEN["bounds"] = bounds
        VARLEN["backend"] = "sdpa-segments"
        ref, _ = varlen_attention(None, q, k, v, None, scaling=256**-0.5)
        VARLEN["backend"] = "torch-varlen"
        got, _ = varlen_attention(None, q, k, v, None, scaling=256**-0.5)
        diff = (got.float() - ref.float()).abs()
        record.update(max_abs_diff=float(diff.max()), mean_abs_diff=float(diff.mean()))
        if float(diff.max()) < 0.05:
            record["backend"] = "torch-varlen"
        else:
            record["reason"] = "varlen_attn disagrees with per-segment SDPA"
    except Exception as exc:  # noqa: BLE001 - recorded; the fallback is used
        record["reason"] = repr(exc)[:500]
    finally:
        VARLEN["bounds"] = None
        VARLEN["calls"] = 0
    VARLEN["backend"] = record["backend"]
    return record


def probe_trainer_state(torch: Any) -> dict[str, Any]:
    """Dtypes in FLA's chunk path for a bf16 input (the trainer path's GDN call): the output,
    the final state, and the per-chunk state snapshots ``h`` (captured by wrapping
    ``chunk_gated_delta_rule_fwd_h`` in FLA's gated_delta_rule chunk module)."""

    if not torch.cuda.is_available():
        return {"skipped": "no CUDA"}
    record: dict[str, Any] = {
        "input_dtype": "torch.bfloat16",
        "hf_teacher_forcing_call": "initial_state=None, output_final_state=False (no cache)",
    }
    try:
        import fla.ops.gated_delta_rule.chunk as gchunk
        from fla.ops.gated_delta_rule import chunk_gated_delta_rule

        original = getattr(gchunk, "chunk_gated_delta_rule_fwd_h", None)
        captured: dict[str, str] = {}

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            result = original(*args, **kwargs)
            captured["h"] = str(result[0].dtype)
            return result

        if original is not None:
            gchunk.chunk_gated_delta_rule_fwd_h = wrapped
        try:
            gen = torch.Generator(device="cuda").manual_seed(42)
            shape = (1, 256, 32, 128)
            q, k, v = (
                torch.randn(*shape, device="cuda", dtype=torch.bfloat16, generator=gen)
                for _ in range(3)
            )
            g = torch.nn.functional.logsigmoid(
                torch.randn(1, 256, 32, device="cuda", generator=gen)
            )
            beta = torch.rand(1, 256, 32, device="cuda", generator=gen).to(torch.bfloat16)
            o, final = chunk_gated_delta_rule(
                q, k, v, g=g, beta=beta, output_final_state=True, use_qk_l2norm_in_kernel=True
            )
        finally:
            if original is not None:
                gchunk.chunk_gated_delta_rule_fwd_h = original
        record.update(
            output_dtype=str(o.dtype),
            final_state_dtype=str(final.dtype),
            chunk_state_snapshot_dtype=captured.get("h", "not captured"),
        )
    except Exception as exc:  # noqa: BLE001 - recorded; the probe is informational
        record["error"] = repr(exc)[:500]
    return record


# --------------------------------------------------------------------------- run


def r4_prompt_indices(config: dict[str, Any]) -> set[int]:
    prompts = g2.load_prompts(config)
    subset = g2.prompt_subset(prompts, config["rollouts"]["prompt_count"])
    return {int(r["prompt_index"]) for r in subset[: config["teacher_force"]["r4_prompts"]]}


def path_members(config: dict[str, Any], sequences: list[dict[str, Any]]) -> dict[str, list[int]]:
    tf = config["teacher_force"]
    r4_prompts = r4_prompt_indices(config)
    return {
        "r1": list(range(len(sequences))),
        "r2": [i for i, s in enumerate(sequences) if s["seed"] in tf["r2_seeds"]],
        "r4": [
            i
            for i, s in enumerate(sequences)
            if s["seed"] in tf["r4_seeds"] and s["prompt_index"] in r4_prompts
        ],
    }


def run_main(args: argparse.Namespace) -> int:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base.set_cache_env(out)
    import numpy as np
    import torch
    import transformers

    config = gb.load_config()
    stop = base.Stop()
    import signal

    signal.signal(signal.SIGUSR1, stop.handler)
    signal.signal(signal.SIGTERM, stop.handler)
    stop_at, source = g2.deadline(args.allocation_minutes)
    evidence = Path(args.evidence)
    if g2.sha256_file(evidence) != args.expected_evidence_sha256:
        raise gb.G2bConfigError("study artifact digest differs from --expected-evidence-sha256")
    tf_input = json.loads(evidence.read_text(encoding="utf-8"))
    if tf_input.get("experiment_id") != config["experiment_id"]:
        raise gb.G2bConfigError("study artifact is not this experiment's tf-input")
    model_id = args.model
    model_cfg = config["models"][model_id]
    sequences = [s for s in tf_input["sequences"] if s["model_id"] == model_id]
    chunk = int(config["teacher_force"]["lm_head_chunk"])
    progress = out / "progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, **fields}
        with progress.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    import fla

    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "teacher-force",
        "model": model_id,
        "started_at": g2.utc_now(),
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "sequences": len(sequences),
        "versions": {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "fla": getattr(fla, "__version__", "?"),
            "python": sys.version,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "paths": {},
    }
    summary["verification"] = g2.verify_model(model_id, model_cfg["receipt_root"])
    device = "cuda"
    register_attention()
    summary["varlen_check"] = check_varlen_backend(torch)
    summary["trainer_state_probe"] = probe_trainer_state(torch)
    log("checks", varlen=summary["varlen_check"], state=summary["trainer_state_probe"])
    t0 = time.time()
    model = base.load_model(torch, g2.MODEL_ROOT / model_id, model_cfg["hf_class"], device)
    summary["load_s"] = round(time.time() - t0, 1)
    switch = GdnSwitch()
    summary["gdn"] = switch.describe()
    gdn_layers = sum(
        1 for t in model.config.get_text_config().layer_types if t == "linear_attention"
    )
    summary["gdn_layers"] = gdn_layers
    members = path_members(config, sequences)
    summary["path_members"] = {k: len(v) for k, v in members.items()}
    lengths = [len(s["completion_ids"]) for s in sequences]
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    total = int(offsets[-1])
    arrays: dict[str, Any] = {}
    pack_id = np.full(len(sequences), -1, dtype=np.int32)
    pack_slot = np.full(len(sequences), -1, dtype=np.int32)
    exit_code = 0

    def put(name: str, index: int, values: Any) -> None:
        arrays.setdefault(name, np.full(total, np.nan, dtype=np.float32))
        arrays[name][offsets[index] : offsets[index + 1]] = values

    for path in PATHS:
        if path == "r4" and next(model.parameters()).dtype != torch.float32:
            model = model.float()
        precision = base.set_precision(
            torch, "r4_torch_fp32" if path == "r4" else "r1_fla_chunk_bf16"
        )
        switch.use(GDN_IMPL[path])
        p0 = time.time()
        done = 0
        status = "complete"
        record: dict[str, Any] = {
            "gdn_impl": GDN_IMPL[path],
            "precision": precision,
            "members": len(members[path]),
        }
        if path == "r2":
            budget = int(config["teacher_force"]["pack_tokens"])
            member_lengths = [len(sequences[i]["prompt_ids"]) + lengths[i] for i in members[path]]
            packs = [
                [members[path][j] for j in pack] for pack in gb.greedy_packs(member_lengths, budget)
            ]
            record.update(packs=len(packs), pack_tokens=budget, varlen_backend=VARLEN["backend"])
            # Single-sequence check: the packed path on one sequence against r1.
            first = members[path][0] if members[path] else None
            if first is not None and "logp_r1" in arrays:
                s = sequences[first]
                (lp, _), _ = score_pack(
                    torch,
                    model,
                    [(s["prompt_ids"] + s["completion_ids"], len(s["prompt_ids"]))],
                    chunk,
                    device,
                )
                ref = arrays["logp_r1"][offsets[first] : offsets[first + 1]]
                diff = np.abs(lp - ref)
                record["single_sequence_vs_r1"] = {
                    "sequence_id": s["sequence_id"],
                    "mean_abs": float(diff.mean()),
                    "max_abs": float(diff.max()),
                }
            for number, pack in enumerate(packs):
                if stop.event.is_set() or time.time() > stop_at:
                    status = "stopped: " + (stop.reason or "deadline")
                    break
                seqs = [
                    (
                        sequences[i]["prompt_ids"] + sequences[i]["completion_ids"],
                        len(sequences[i]["prompt_ids"]),
                    )
                    for i in pack
                ]
                calls0, packed0, attn0 = switch.calls, switch.packed_calls, VARLEN["calls"]
                results, counters = score_pack(torch, model, seqs, chunk, device)
                if (
                    switch.calls - calls0 != gdn_layers
                    or switch.packed_calls - packed0 != gdn_layers
                    or counters["conv_segmented"] != gdn_layers
                    or VARLEN["calls"] - attn0 != model_cfg["attention_layers"]
                ):
                    raise RuntimeError(
                        f"r2: packed path not effective in pack {number}: "
                        f"{switch.calls - calls0} GDN, {counters} conv, "
                        f"{VARLEN['calls'] - attn0} attention calls"
                    )
                for slot, (i, (lp, _en)) in enumerate(zip(pack, results, strict=True)):
                    put("logp_r2", i, lp)
                    pack_id[i] = number
                    pack_slot[i] = slot
                    done += 1
        else:
            for i in members[path]:
                if stop.event.is_set() or time.time() > stop_at:
                    status = "stopped: " + (stop.reason or "deadline")
                    break
                s = sequences[i]
                ids = s["prompt_ids"] + s["completion_ids"]
                calls0 = switch.calls
                with base.sdpa_context(
                    torch, "r4_torch_fp32" if path == "r4" else "r1_fla_chunk_bf16"
                ):
                    lp, en = base.score_sequence(
                        torch, model, ids, len(s["prompt_ids"]), chunk, device
                    )
                if switch.calls - calls0 != gdn_layers:
                    raise RuntimeError(
                        f"{path}: GDN swap not effective ({switch.calls - calls0} calls)"
                    )
                put(f"logp_{path}", i, lp)
                put(f"ent_{path}", i, en)
                done += 1
        record.update(
            status=status,
            sequences_scored=done,
            wall_s=round(time.time() - p0, 1),
            param_dtype=str(next(model.parameters()).dtype),
        )
        summary["paths"][path] = record
        log("path-done", model=model_id, path=path, **record)
        if status != "complete":
            exit_code = 3
        g2.write_json(out / "summary.json", summary)
    np.savez_compressed(
        out / f"tf-{model_id}.npz",
        offsets=offsets,
        prompt_len=np.asarray([len(s["prompt_ids"]) for s in sequences], dtype=np.int32),
        token_ids=np.asarray([t for s in sequences for t in s["completion_ids"]], dtype=np.int32),
        pack_id=pack_id,
        pack_slot=pack_slot,
        **arrays,
    )
    g2.write_json(
        out / f"tf-{model_id}-sequences.json",
        [{k: s[k] for k in ("sequence_id", "arm", "prompt_index", "seed")} for s in sequences],
    )
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = stop.reason
    g2.write_json(out / "summary.json", summary)
    if stop.reason:
        g2.write_checkpoint_marker(
            stop.reason, "g2b teacher-force: finished paths saved; no resume"
        )
    return exit_code


# --------------------------------------------------------------------------- selftest


def selftest_main(_args: argparse.Namespace) -> int:
    """CPU, tiny random Qwen3.5 (VL wrapper) in fp32: the packed path equals per-sequence
    forwards (CPU, fp32: exactly); without the per-sequence convolution or GDN the packed forward
    leaks across sequences (so the check has teeth); the scorer equals a plain forward."""

    import numpy as np
    import torch
    import transformers

    torch.manual_seed(42)
    register_attention()
    report: dict[str, Any] = {"transformers": transformers.__version__, "torch": torch.__version__}
    text = dict(
        vocab_size=512,
        hidden_size=64,
        intermediate_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=16,
        linear_num_key_heads=2,
        linear_num_value_heads=4,
        linear_key_head_dim=16,
        linear_value_head_dim=16,
        linear_conv_kernel_dim=4,
        full_attention_interval=4,
        attn_output_gate=True,
        layer_types=["linear_attention"] * 3 + ["full_attention"],
        tie_word_embeddings=True,
    )
    vl_config = transformers.Qwen3_5Config(
        text_config=text,
        vision_config=dict(
            depth=1, hidden_size=32, intermediate_size=64, num_heads=2, out_hidden_size=64
        ),
    )
    vl_config.tie_word_embeddings = True
    model = transformers.Qwen3_5ForConditionalGeneration(vl_config).float().eval()
    switch = GdnSwitch()
    switch.use("torch_chunk_fp32")
    lengths = [70, 130, 45]
    seqs = [([int(i) for i in torch.randint(0, 512, (n,))], 10) for n in lengths]
    unpacked = [base.score_sequence(torch, model, ids, p, 32, "cpu") for ids, p in seqs]
    calls0 = switch.calls
    packed, counters = score_pack(torch, model, seqs, 32, "cpu")
    report["gdn_calls_packed"] = switch.calls - calls0
    report["packed_gdn_calls"] = switch.packed_calls
    report["conv_segmented"] = counters["conv_segmented"]
    report["attention_calls"] = VARLEN["calls"]
    diffs = [float(np.abs(a[0] - b[0]).max()) for a, b in zip(unpacked, packed, strict=True)]
    ent_diffs = [float(np.abs(a[1] - b[1]).max()) for a, b in zip(unpacked, packed, strict=True)]
    report["packed_vs_unpacked_max_abs_logp"] = diffs
    report["packed_vs_unpacked_max_abs_entropy"] = ent_diffs
    leak_conv, _ = score_pack(torch, model, seqs, 32, "cpu", segment_conv=False)
    report["conv_leak_max_abs_logp"] = [
        float(np.abs(a[0] - b[0]).max()) for a, b in zip(unpacked, leak_conv, strict=True)
    ]
    switch.use("torch_chunk_fp32", segment_torch=False)
    leak_gdn, _ = score_pack(torch, model, seqs, 32, "cpu")
    report["gdn_leak_max_abs_logp"] = [
        float(np.abs(a[0] - b[0]).max()) for a, b in zip(unpacked, leak_gdn, strict=True)
    ]
    switch.use("torch_chunk_fp32")
    with torch.inference_mode():
        ids, p = seqs[1]
        logits = model(input_ids=torch.tensor([ids]), use_cache=False).logits[0].float()
        ref = torch.log_softmax(logits, -1)[p - 1 : -1].gather(-1, torch.tensor(ids[p:])[:, None])[
            :, 0
        ]
    report["scorer_vs_forward_max_abs"] = float(np.abs(unpacked[1][0] - ref.numpy()).max())
    gdn_layers = 3
    report["ok"] = bool(
        report["gdn_calls_packed"] == gdn_layers
        and report["packed_gdn_calls"] == gdn_layers
        and report["conv_segmented"] == gdn_layers
        and report["attention_calls"] == 1
        and max(diffs) < 1e-4
        and max(ent_diffs) < 1e-4
        and max(report["conv_leak_max_abs_logp"][1:]) > 1e-5
        and report["conv_leak_max_abs_logp"][0] < 1e-4
        and max(report["gdn_leak_max_abs_logp"][1:]) > 1e-5
        and report["scorer_vs_forward_max_abs"] < 1e-4
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("selftest")
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--evidence", required=True)
    run.add_argument("--expected-evidence-sha256", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        config = gb.load_config()
        print(
            json.dumps(
                {
                    "experiment_id": config["experiment_id"],
                    "paths": PATHS,
                    "gdn_impl": GDN_IMPL,
                    "teacher_force": config["teacher_force"],
                    "r4_prompts": sorted(r4_prompt_indices(config)),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "selftest":
        return selftest_main(args)
    return run_main(args)


if __name__ == "__main__":
    sys.exit(main())
