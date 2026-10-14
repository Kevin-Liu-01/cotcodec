#!/usr/bin/env python3
"""G2 exploratory pilot, job 2: teacher-force the vLLM rollouts through the trainer path.

EXPLORATORY (experiments/g2/g2-pilot-v1.yaml). Runs inside a research image (torch 2.11,
transformers 5.15, flash-linear-attention 0.5.2) on the docker-research lane. Its input is the
rollout job's ``tf-input.json``, mounted as the lane's hash-bound study artifact.

Paths (each one full forward per sequence, no packing, batch 1, no KV cache):

* ``r1_fla_chunk_bf16``: HF transformers in bf16, SDPA restricted to flash or memory-efficient
  kernels; for the GDN hybrid the gated delta rule is FLA's ``chunk_gated_delta_rule`` (what
  verl's Qwen3.5 trainer path calls). For the dense control this is plain HF bf16.
* ``r3_fla_recurrent_bf16``: as r1, with FLA's ``fused_recurrent_gated_delta_rule`` instead
  (hybrid only): the chunk-vs-recurrent attribution arm.
* ``r4_torch_fp32``: the fp32 reference: the bf16 weights upcast exactly to fp32, TF32 off,
  memory-efficient SDPA in fp32 (GQA by repeated K/V), and for the hybrid HF's torch-native
  chunked gated delta rule (fp32 throughout). Run on the ``fp32_seeds`` rollouts only.

The LM head runs on 2,048-position chunks of the final hidden states: logits in the model's
dtype, then fp32 log-softmax, as the trainer does. Per completion token it records the
log-prob of the rollout's token and the entropy of the full distribution. The GDN function
is swapped by replacing ``modeling_qwen3_5.torch_chunk_gated_delta_rule`` (the module global
the GatedDeltaNet forward calls), and a call counter proves the swap took effect.

Subcommands: ``plan``, ``selftest`` (CPU, tiny random models), ``run``.
"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as g2  # noqa: E402

PATHS = ("r1_fla_chunk_bf16", "r3_fla_recurrent_bf16", "r4_torch_fp32")
GDN_IMPL = {
    "r1_fla_chunk_bf16": "fla_chunk",
    "r3_fla_recurrent_bf16": "fla_fused_recurrent",
    "r4_torch_fp32": "torch_chunk_fp32",
}


def set_cache_env(out: Path) -> None:
    """JIT caches on the run directory: the default profile mounts /tmp noexec."""

    for key, sub in (
        ("TRITON_CACHE_DIR", "triton"),
        ("TRITON_HOME", "triton-home"),
        ("TORCHINDUCTOR_CACHE_DIR", "inductor"),
        ("CUDA_CACHE_PATH", "cuda"),
        ("XDG_CACHE_HOME", "xdg"),
    ):
        path = out / "cache" / sub
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)


# --------------------------------------------------------------------------- GDN swap


class GdnSwitch:
    """Replaces the gated-delta-rule entry point of transformers' Qwen3.5 module."""

    def __init__(self) -> None:
        import transformers.models.qwen3_5.modeling_qwen3_5 as mq

        self.module = mq
        self.original = mq.torch_chunk_gated_delta_rule
        self.torch_chunk = inspect.unwrap(self.original)
        if self.torch_chunk.__name__ != "torch_chunk_gated_delta_rule" or (
            self.torch_chunk.__module__ != mq.__name__
        ):
            raise RuntimeError("could not unwrap the torch-native chunked gated delta rule")
        self.calls = 0
        self.impl = "unset"

    def describe(self) -> dict[str, Any]:
        info = {
            "original": f"{getattr(self.original, '__module__', '?')}."
            f"{getattr(self.original, '__qualname__', '?')}",
            "torch_chunk": f"{self.torch_chunk.__module__}.{self.torch_chunk.__qualname__}",
        }
        resolved = None
        for cell in getattr(self.original, "__closure__", None) or ():
            value = cell.cell_contents
            if callable(value) and value is not self.torch_chunk:
                resolved = f"{getattr(value, '__module__', '?')}.{getattr(value, '__qualname__', '?')}"
        info["stock_resolution"] = resolved
        return info

    def use(self, impl: str) -> None:
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
            if impl != "torch_chunk_fp32":
                kwargs["cu_seqlens"] = cu_seqlens
            return fn(query, key, value, **kwargs)

        self.module.torch_chunk_gated_delta_rule = gated_delta_rule
        self.impl = impl
        self.calls = 0


# --------------------------------------------------------------------------- precision


def set_precision(torch: Any, path: str) -> dict[str, Any]:
    fp32 = path == "r4_torch_fp32"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    import transformers.integrations.sdpa_attention as sdpa

    if not hasattr(sdpa, "_g2_stock_use_gqa"):
        sdpa._g2_stock_use_gqa = sdpa.use_gqa_in_sdpa
    # fp32: no GQA flag, so K/V are repeated and the memory-efficient kernel can run.
    sdpa.use_gqa_in_sdpa = (lambda *a, **k: False) if fp32 else sdpa._g2_stock_use_gqa
    return {
        "allow_tf32": False,
        "float32_matmul_precision": "highest",
        "sdpa_gqa_flag": "off (repeat_kv)" if fp32 else "stock",
        "sdpa_backends": ["EFFICIENT_ATTENTION"] if fp32 else ["FLASH_ATTENTION", "EFFICIENT_ATTENTION"],
    }


def sdpa_context(torch: Any, path: str) -> Any:
    if not torch.cuda.is_available():
        return contextlib.nullcontext()
    from torch.nn.attention import SDPBackend, sdpa_kernel

    if path == "r4_torch_fp32":
        return sdpa_kernel([SDPBackend.EFFICIENT_ATTENTION])
    return sdpa_kernel([SDPBackend.FLASH_ATTENTION, SDPBackend.EFFICIENT_ATTENTION])


# --------------------------------------------------------------------------- scoring


def score_sequence(
    torch: Any, model: Any, ids: list[int], prompt_len: int, chunk: int, device: str
) -> tuple[Any, Any]:
    """Log-prob of each completion token and the entropy of its full distribution (fp32)."""

    with torch.inference_mode():
        x = torch.tensor([ids], dtype=torch.long, device=device)
        hidden = model.model(input_ids=x, use_cache=False).last_hidden_state[0]
        rows = hidden[prompt_len - 1 : len(ids) - 1]
        target = x[0, prompt_len:]
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


def load_model(torch: Any, model_dir: Path, class_name: str, device: str) -> Any:
    import transformers

    cls = getattr(transformers, class_name)
    model = cls.from_pretrained(
        str(model_dir), dtype=torch.bfloat16, attn_implementation="sdpa", trust_remote_code=False
    )
    return model.to(device).eval()


# --------------------------------------------------------------------------- run


class Stop:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.reason: str | None = None

    def handler(self, signum: int, _frame: Any) -> None:
        self.reason = signal.Signals(signum).name
        self.event.set()


def run_main(args: argparse.Namespace) -> int:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    set_cache_env(out)
    import numpy as np
    import torch
    import transformers

    config = g2.load_config()
    stop = Stop()
    signal.signal(signal.SIGUSR1, stop.handler)
    signal.signal(signal.SIGTERM, stop.handler)
    stop_at, source = g2.deadline(args.allocation_minutes)
    evidence = Path(args.evidence)
    if g2.sha256_file(evidence) != args.expected_evidence_sha256:
        raise g2.G2ConfigError("study artifact digest differs from --expected-evidence-sha256")
    tf_input = json.loads(evidence.read_text(encoding="utf-8"))
    if tf_input.get("experiment_id") != config["experiment_id"]:
        raise g2.G2ConfigError("study artifact is not this experiment's tf-input")
    fp32_seeds = set(config["teacher_force"]["fp32_seeds"])
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
        "started_at": g2.utc_now(),
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "rollout_git_sha": tf_input.get("git_sha"),
        "versions": {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "fla": getattr(fla, "__version__", "?"),
            "python": sys.version,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "lane": {
            k: os.environ.get(k)
            for k in ("COTCODEC_GIT_SHA", "COTCODEC_SOURCE_SHA256", "COTCODEC_MODEL_ID")
        },
        "models": {},
    }
    import importlib.util

    summary["versions"]["causal_conv1d_installed"] = (
        importlib.util.find_spec("causal_conv1d") is not None
    )
    summary["versions"]["kernels_installed"] = importlib.util.find_spec("kernels") is not None

    # Verify every model up front, the secondary ones in a thread while the GPU works.
    verifications: dict[str, Any] = {}

    def verify_all() -> None:
        for model_id, model in config["models"].items():
            try:
                verifications[model_id] = g2.verify_model(model_id, model["receipt_root"])
            except Exception as exc:  # noqa: BLE001 - recorded; the model is skipped
                verifications[model_id] = {"error": repr(exc)}

    verifier = threading.Thread(target=verify_all, daemon=True)
    verifier.start()
    device = "cuda"
    exit_code = 0
    for model_id, model_cfg in config["models"].items():
        sequences = [s for s in tf_input["sequences"] if s["model_id"] == model_id]
        record: dict[str, Any] = {"sequences": len(sequences), "paths": {}}
        summary["models"][model_id] = record
        while model_id not in verifications and verifier.is_alive():
            time.sleep(1.0)
        record["verification"] = verifications.get(model_id)
        if not sequences or "error" in (verifications.get(model_id) or {"error": "missing"}):
            record["status"] = "skipped"
            exit_code = 3
            continue
        t0 = time.time()
        model = load_model(torch, g2.MODEL_ROOT / model_id, model_cfg["hf_class"], device)
        record["load_s"] = round(time.time() - t0, 1)
        hybrid = model_cfg["family"] == "gdn-attention-hybrid"
        switch = GdnSwitch() if hybrid else None
        if switch is not None:
            record["gdn"] = switch.describe()
            record["gdn_layers"] = sum(
                1 for t in model.config.get_text_config().layer_types if t == "linear_attention"
            )
        arrays: dict[str, Any] = {}
        total = sum(len(s["completion_ids"]) for s in sequences)
        offsets = np.zeros(len(sequences) + 1, dtype=np.int64)
        offsets[1:] = np.cumsum([len(s["completion_ids"]) for s in sequences])
        for path in model_cfg["tf_paths"]:
            if stop.event.is_set():
                break
            if path == "r4_torch_fp32" and next(model.parameters()).dtype != torch.float32:
                model = model.float()
            precision = set_precision(torch, path)
            if switch is not None:
                switch.use(GDN_IMPL[path])
            logp = np.full(total, np.nan, dtype=np.float32)
            ent = np.full(total, np.nan, dtype=np.float32)
            done = 0
            fallback = 0
            p0 = time.time()
            status = "complete"
            for index, seq in enumerate(sequences):
                if path == "r4_torch_fp32" and seq["seed"] not in fp32_seeds:
                    continue
                if stop.event.is_set() or time.time() > stop_at:
                    status = "stopped: " + (stop.reason or "deadline")
                    break
                ids = seq["prompt_ids"] + seq["completion_ids"]
                prompt_len = len(seq["prompt_ids"])
                calls_before = switch.calls if switch else 0
                try:
                    with sdpa_context(torch, path):
                        lp, en = score_sequence(torch, model, ids, prompt_len, chunk, device)
                except RuntimeError as exc:
                    if "No available kernel" not in str(exc):
                        raise
                    fallback += 1
                    with contextlib.nullcontext():
                        lp, en = score_sequence(torch, model, ids, prompt_len, chunk, device)
                if switch is not None and switch.calls - calls_before != record["gdn_layers"]:
                    raise RuntimeError(
                        f"{path}: GDN swap not effective ({switch.calls - calls_before} calls)"
                    )
                logp[offsets[index] : offsets[index + 1]] = lp
                ent[offsets[index] : offsets[index + 1]] = en
                done += 1
            arrays[f"logp_{path}"] = logp
            arrays[f"ent_{path}"] = ent
            record["paths"][path] = {
                "status": status,
                "sequences_scored": done,
                "wall_s": round(time.time() - p0, 1),
                "gdn_impl": switch.impl if switch else None,
                "precision": precision,
                "sdpa_unrestricted_fallbacks": fallback,
                "param_dtype": str(next(model.parameters()).dtype),
            }
            log("path-done", model=model_id, path=path, **record["paths"][path])
            if status != "complete":
                exit_code = 3
        np.savez_compressed(
            out / f"tf-{model_id}.npz",
            offsets=offsets,
            prompt_len=np.asarray([len(s["prompt_ids"]) for s in sequences], dtype=np.int32),
            token_ids=np.asarray(
                [t for s in sequences for t in s["completion_ids"]], dtype=np.int32
            ),
            **arrays,
        )
        g2.write_json(
            out / f"tf-{model_id}-sequences.json",
            [{k: s[k] for k in ("sequence_id", "prompt_index", "seed")} for s in sequences],
        )
        del model
        torch.cuda.empty_cache()
        g2.write_json(out / "summary.json", summary)
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = stop.reason
    g2.write_json(out / "summary.json", summary)
    if stop.reason:
        g2.write_checkpoint_marker(
            stop.reason, "teacher-force: finished paths saved; no resume (a rerun is a new job)"
        )
    return exit_code


# --------------------------------------------------------------------------- selftest


def selftest_main(_args: argparse.Namespace) -> int:
    """CPU: tiny random Qwen3.5 (text and VL wrapper) and Qwen3 models; checks the GDN swap,
    the chunked LM-head scorer against a plain forward, and torch chunk vs recurrent in fp32."""

    import torch
    import transformers
    import transformers.models.qwen3_5.modeling_qwen3_5 as mq

    torch.manual_seed(42)
    report: dict[str, Any] = {"transformers": transformers.__version__, "torch": torch.__version__}
    try:
        import fla.ops.gated_delta_rule as fgdr

        report["fla_import"] = sorted(n for n in dir(fgdr) if "gated_delta_rule" in n)
    except Exception as exc:  # noqa: BLE001 - recorded
        report["fla_import_error"] = repr(exc)
    text = dict(
        vocab_size=512, hidden_size=64, intermediate_size=128, num_hidden_layers=4,
        num_attention_heads=4, num_key_value_heads=2, head_dim=16, linear_num_key_heads=2,
        linear_num_value_heads=4, linear_key_head_dim=16, linear_value_head_dim=16,
        linear_conv_kernel_dim=4, full_attention_interval=4, attn_output_gate=True,
        layer_types=["linear_attention"] * 3 + ["full_attention"], tie_word_embeddings=True,
    )  # fmt: skip
    vl_config = transformers.Qwen3_5Config(
        text_config=text,
        vision_config=dict(depth=1, hidden_size=32, intermediate_size=64, num_heads=2,
                           out_hidden_size=64),
    )  # fmt: skip
    vl_config.tie_word_embeddings = True
    model = transformers.Qwen3_5ForConditionalGeneration(vl_config).float().eval()
    switch = GdnSwitch()
    report["gdn_describe"] = switch.describe()
    switch.use("torch_chunk_fp32")
    ids = [int(i) for i in torch.randint(0, 512, (150,))]
    prompt_len = 20
    lp, en = score_sequence(torch, model, ids, prompt_len, 32, "cpu")
    report["gdn_calls_per_forward"] = switch.calls
    with torch.inference_mode():
        logits = model(input_ids=torch.tensor([ids]), use_cache=False).logits[0].float()
        ref = torch.log_softmax(logits, -1)[prompt_len - 1 : -1]
        ref_lp = ref.gather(-1, torch.tensor(ids[prompt_len:])[:, None])[:, 0].numpy()
        ref_en = -(ref.exp() * ref).sum(-1).numpy()
    report["scorer_max_abs_logp_diff"] = float(abs(lp - ref_lp).max())
    report["scorer_max_abs_entropy_diff"] = float(abs(en - ref_en).max())
    # torch chunk vs torch recurrent (fp32) on random GDN inputs.
    q, k, v = (torch.randn(1, 300, 4, 16) for _ in range(3))
    g = -torch.rand(1, 300, 4)
    beta = torch.rand(1, 300, 4)
    recurrent = inspect.unwrap(mq.torch_recurrent_gated_delta_rule)
    a, _ = switch.torch_chunk(q, k, v, g=g, beta=beta, use_qk_l2norm_in_kernel=True)
    b, _ = recurrent(q, k, v, g=g, beta=beta, initial_state=None, output_final_state=False,
                     use_qk_l2norm_in_kernel=True)  # fmt: skip
    report["torch_chunk_vs_recurrent_max_abs"] = float((a - b).abs().max())
    dense = transformers.Qwen3ForCausalLM(
        transformers.Qwen3Config(vocab_size=512, hidden_size=64, intermediate_size=128,
                                 num_hidden_layers=2, num_attention_heads=4,
                                 num_key_value_heads=2, head_dim=16)
    ).float().eval()  # fmt: skip
    lp2, _ = score_sequence(torch, dense, ids, prompt_len, 32, "cpu")
    with torch.inference_mode():
        ref2 = torch.log_softmax(dense(input_ids=torch.tensor([ids])).logits[0].float(), -1)
        ref2_lp = ref2[prompt_len - 1 : -1].gather(-1, torch.tensor(ids[prompt_len:])[:, None])
    report["dense_scorer_max_abs_logp_diff"] = float(abs(lp2 - ref2_lp[:, 0].numpy()).max())
    report["ok"] = (
        report["gdn_calls_per_forward"] == 3
        and report["scorer_max_abs_logp_diff"] < 1e-4
        and report["scorer_max_abs_entropy_diff"] < 1e-4
        and report["dense_scorer_max_abs_logp_diff"] < 1e-4
        and report["torch_chunk_vs_recurrent_max_abs"] < 1e-3
        and "fla_import" in report
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
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        config = g2.load_config()
        print(
            json.dumps(
                {
                    "experiment_id": config["experiment_id"],
                    "paths": {m: c["tf_paths"] for m, c in config["models"].items()},
                    "fp32_seeds": config["teacher_force"]["fp32_seeds"],
                    "lm_head_chunk": config["teacher_force"]["lm_head_chunk"],
                    "gdn_impl": GDN_IMPL,
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
