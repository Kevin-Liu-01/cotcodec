#!/usr/bin/env python3
"""Probe Qwen3.5-4B-Base's real recurrent-cache interface on one H100."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
MODEL_ID = "qwen3.5-4b-base"
EXPECTED_REVISION = "1001bb4d826a52d1f399e183466143f4da7b741b"
EXPECTED_ARTIFACT_ROOT = "c7fbfd6bd1c73b9a0080decf794f5e4333c955f2704591affc61b0a9ac850e42"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def judge_interface(metrics: Mapping[str, Any]) -> dict[str, bool]:
    """Apply preregistered interface-only gates to scalar observations."""

    cosine = metrics.get("logit_cosine")
    max_abs = metrics.get("logit_max_abs")
    return {
        "registered_topology": (
            metrics.get("layers") == 32
            and metrics.get("linear_layers") == 24
            and metrics.get("full_attention_layers") == 8
        ),
        "linear_states_present": metrics.get("linear_states_present") == 24,
        "linear_state_shape": metrics.get("linear_state_shape_exact") is True,
        "full_attention_cache_present": metrics.get("full_attention_caches_present") == 8,
        "finite_states": metrics.get("all_states_finite") is True,
        "prefix_cache_length": metrics.get("prefix_cache_length_exact") is True,
        "continuation_cache_length": metrics.get("continuation_cache_length_exact") is True,
        "continuation_updates_every_linear_layer": metrics.get("changed_linear_layers") == 24,
        "cached_vs_one_shot_cosine": (
            isinstance(cosine, (int, float))
            and not isinstance(cosine, bool)
            and math.isfinite(float(cosine))
            and float(cosine) >= 0.999
        ),
        "cached_vs_one_shot_max_abs": (
            isinstance(max_abs, (int, float))
            and not isinstance(max_abs, bool)
            and math.isfinite(float(max_abs))
            and float(max_abs) <= 0.25
        ),
    }


def _tensor_summary(tensor: Any, torch: Any) -> dict[str, Any]:
    value = tensor.detach()
    finite = bool(torch.isfinite(value).all().item())
    return {
        "shape": list(value.shape),
        "dtype": str(value.dtype),
        "finite": finite,
        "norm": float(torch.linalg.vector_norm(value.float()).item()) if finite else None,
    }


def _cache_projection(cache: Any, layer_types: list[str], torch: Any) -> dict[str, Any]:
    linear: list[dict[str, Any]] = []
    full: list[dict[str, Any]] = []
    for index, layer_type in enumerate(layer_types):
        layer = cache.layers[index]
        if layer_type == "linear_attention":
            recurrent = layer.recurrent_states[0]
            convolution = layer.conv_states[0]
            linear.append(
                {
                    "layer": index,
                    "recurrent": (
                        _tensor_summary(recurrent, torch) if recurrent is not None else None
                    ),
                    "convolution": (
                        _tensor_summary(convolution, torch) if convolution is not None else None
                    ),
                }
            )
        else:
            keys = getattr(layer, "keys", None)
            values = getattr(layer, "values", None)
            full.append(
                {
                    "layer": index,
                    "keys": _tensor_summary(keys, torch) if keys is not None else None,
                    "values": _tensor_summary(values, torch) if values is not None else None,
                }
            )
    return {
        "sequence_length": int(cache.get_seq_length()),
        "linear": linear,
        "full_attention": full,
    }


def _metrics(
    *,
    prefix: Mapping[str, Any],
    continued: Mapping[str, Any],
    layer_types: list[str],
    prefix_tokens: int,
    total_tokens: int,
    logit_cosine: float,
    logit_max_abs: float,
) -> dict[str, Any]:
    recurrent = [row["recurrent"] for row in prefix["linear"]]
    full = prefix["full_attention"]
    changed = sum(
        1
        for before, after in zip(prefix["linear"], continued["linear"], strict=True)
        if before["recurrent"] is not None
        and after["recurrent"] is not None
        and before["recurrent"]["norm"] is not None
        and after["recurrent"]["norm"] is not None
        and before["recurrent"]["norm"] != after["recurrent"]["norm"]
    )
    return {
        "layers": len(layer_types),
        "linear_layers": layer_types.count("linear_attention"),
        "full_attention_layers": layer_types.count("full_attention"),
        "linear_states_present": sum(item is not None for item in recurrent),
        "linear_state_shape_exact": all(
            item is not None and item["shape"] == [1, 32, 128, 128] for item in recurrent
        ),
        "full_attention_caches_present": sum(
            row["keys"] is not None and row["values"] is not None for row in full
        ),
        "all_states_finite": all(
            item is not None and item["finite"] for item in recurrent
        )
        and all(
            row["keys"] is not None
            and row["values"] is not None
            and row["keys"]["finite"]
            and row["values"]["finite"]
            for row in full
        ),
        "prefix_cache_length_exact": prefix["sequence_length"] == prefix_tokens,
        "continuation_cache_length_exact": continued["sequence_length"] == total_tokens,
        "changed_linear_layers": changed,
        "logit_cosine": logit_cosine,
        "logit_max_abs": logit_max_abs,
    }


def run_doctor(
    *, model_root: Path, receipt_root: Path, output: Path, prompt: str
) -> dict[str, Any]:
    started = time.perf_counter()
    from scripts.fetch_open_model import load_registry, verify_receipt

    registry = load_registry(PROJECT_ROOT / "models" / "registry.yaml")
    entry = registry["models"][MODEL_ID]
    receipt = verify_receipt(MODEL_ID, entry, model_root, receipt_root)
    if receipt["revision"] != EXPECTED_REVISION:
        raise ValueError("Qwen3.5-4B-Base revision drifted")
    if receipt["artifact_root_sha256"] != EXPECTED_ARTIFACT_ROOT:
        raise ValueError("Qwen3.5-4B-Base artifact root drifted")

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("interface doctor requires exactly one visible CUDA GPU")
    snapshot = model_root / MODEL_ID
    tokenizer = AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        snapshot,
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype=torch.bfloat16,
        device_map={"": "cuda:0"},
        attn_implementation="eager",
    )
    model.eval()
    text_config = model.config.text_config
    layer_types = list(text_config.layer_types)
    input_ids = tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids
    if input_ids.shape[1] < 5:
        raise ValueError("doctor prompt tokenized to fewer than five tokens")
    input_ids = input_ids.to("cuda:0")
    prefix_ids = input_ids[:, :-1]
    continuation_ids = input_ids[:, -1:]
    with torch.inference_mode():
        prefix_output = model(
            input_ids=prefix_ids,
            attention_mask=torch.ones_like(prefix_ids),
            use_cache=True,
            logits_to_keep=1,
            return_dict=True,
        )
        prefix_projection = _cache_projection(
            prefix_output.past_key_values, layer_types, torch
        )
        continued_output = model(
            input_ids=continuation_ids,
            attention_mask=torch.ones_like(input_ids),
            past_key_values=prefix_output.past_key_values,
            use_cache=True,
            logits_to_keep=1,
            return_dict=True,
        )
        continued_projection = _cache_projection(
            continued_output.past_key_values, layer_types, torch
        )
        one_shot_output = model(
            input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids),
            use_cache=False,
            logits_to_keep=1,
            return_dict=True,
        )
    cached_logits = continued_output.logits[0, -1].float()
    one_shot_logits = one_shot_output.logits[0, -1].float()
    cosine = float(
        torch.nn.functional.cosine_similarity(cached_logits, one_shot_logits, dim=0).item()
    )
    max_abs = float(torch.max(torch.abs(cached_logits - one_shot_logits)).item())
    metrics = _metrics(
        prefix=prefix_projection,
        continued=continued_projection,
        layer_types=layer_types,
        prefix_tokens=int(prefix_ids.shape[1]),
        total_tokens=int(input_ids.shape[1]),
        logit_cosine=cosine,
        logit_max_abs=max_abs,
    )
    gates = judge_interface(metrics)
    result = {
        "schema_version": 1,
        "doctor": "qwen35-recurrent-state-interface",
        "status": (
            "QWEN35_STATE_INTERFACE_PASS"
            if all(gates.values())
            else "QWEN35_STATE_INTERFACE_FAIL"
        ),
        "evidence_grade": "REAL_MODEL_INTERFACE_ONLY",
        "claim_boundary": (
            "Loads the pinned base checkpoint and observes cache topology, finite recurrent "
            "states, one-token state updates, and cached/one-shot logit parity. It measures "
            "no task accuracy, language effect, causal mechanism, training, or publication claim."
        ),
        "model": {
            "model_id": MODEL_ID,
            "revision": receipt["revision"],
            "artifact_root_sha256": receipt["artifact_root_sha256"],
            "receipt_sha256": _sha256_file(receipt_root / f"{MODEL_ID}.json"),
        },
        "source": {
            "git_sha": os.environ.get("COTCODEC_GIT_SHA"),
            "source_sha256": os.environ.get("COTCODEC_SOURCE_SHA256"),
            "doctor_sha256": _sha256_file(Path(__file__)),
        },
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "dtype": "bfloat16",
            "attention_implementation": "eager",
        },
        "prompt_token_ids_sha256": hashlib.sha256(
            input_ids.detach().cpu().numpy().tobytes()
        ).hexdigest(),
        "prefix_cache": prefix_projection,
        "continued_cache": continued_projection,
        "metrics": metrics,
        "gates": gates,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _atomic_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, default=Path("/model-cache/cotcodec-models"))
    parser.add_argument(
        "--receipt-root", type=Path, default=Path("/model-cache/cotcodec-receipts")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--prompt",
        default="A blue lantern crossed the quiet bridge before sunrise, then stopped.",
    )
    args = parser.parse_args()
    result = run_doctor(
        model_root=args.model_root,
        receipt_root=args.receipt_root,
        output=args.output,
        prompt=args.prompt,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "metrics": result["metrics"],
                "gates": result["gates"],
                "receipt": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "QWEN35_STATE_INTERFACE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
