#!/usr/bin/env python3
"""Run a deterministic, local-only forward/generation smoke on a fetched LM."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import tempfile
from pathlib import Path
from typing import Any

from fetch_open_model import (
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
    ModelRegistryError,
    load_registry,
    verify_receipt,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "model-smokes"


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_id")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--prompt", default="The checksum of an immutable model is")
    parser.add_argument("--max-new-tokens", type=int, default=8)
    args = parser.parse_args()

    registry = load_registry(args.registry.resolve())
    if args.model_id not in registry["models"]:
        raise ModelRegistryError(f"unknown model id: {args.model_id}")
    entry = registry["models"][args.model_id]
    if entry["backend"] != "huggingface":
        raise ModelRegistryError("this smoke only supports local Hugging Face snapshots")
    if entry["runtime"] not in {"transformers"}:
        raise ModelRegistryError(
            f"runtime {entry['runtime']!r} needs its dedicated reviewed loader"
        )
    if entry["trust_remote_code"]:
        raise ModelRegistryError("refusing to execute a trust_remote_code model")

    receipt = verify_receipt(
        args.model_id,
        entry,
        args.model_root.resolve(),
        args.receipt_root.resolve(),
    )
    if receipt.get("mode") != "full":
        raise ModelRegistryError("a full model receipt is required for execution")

    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    snapshot = args.model_root.resolve() / args.model_id
    tokenizer = AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        snapshot,
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype="auto",
    )
    model.eval()
    inputs = tokenizer(args.prompt, return_tensors="pt")
    if next(model.parameters()).is_cuda:
        inputs = {key: value.cuda() for key, value in inputs.items()}

    with torch.inference_mode():
        forward = model(**inputs, use_cache=True)
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=args.max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
        )
    logits = forward.logits.detach().float()
    if not torch.isfinite(logits).all():
        raise ModelRegistryError("non-finite logits in local model smoke")

    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    output = {
        "schema_version": 1,
        "model_id": args.model_id,
        "revision": receipt["revision"],
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "seed": 42,
        "prompt": args.prompt,
        "prompt_tokens": int(inputs["input_ids"].shape[-1]),
        "generated_tokens": int(generated.shape[-1] - inputs["input_ids"].shape[-1]),
        "generated_text": tokenizer.decode(generated[0], skip_special_tokens=True),
        "parameter_count": parameter_count,
        "logits_shape": list(logits.shape),
        "logits_mean": float(logits.mean()),
        "logits_std": float(logits.std()),
        "logits_finite": math.isfinite(float(logits.mean()))
        and math.isfinite(float(logits.std())),
        "device": str(next(model.parameters()).device),
    }
    output_path = args.output_root.resolve() / f"{args.model_id}.json"
    atomic_json(output_path, output)
    print(json.dumps({"status": "PASS", "output": str(output_path), **output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
