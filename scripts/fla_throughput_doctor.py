#!/usr/bin/env python3
"""Measure training throughput of small GDN/attention hybrids on one GPU.

Stage-0 infrastructure evidence for directions 19-22: every budget ledger in the
2026-09-01 proposals assumed "125M to 1000N tokens ~ 8 h at 40% MFU" without a
measurement. This doctor times forward+backward+optimizer steps for registered
model shapes with flash-linear-attention kernels and writes a JSON receipt with
tokens/s, achieved MFU against the H100 dense BF16 peak, and exact library
versions. It is not a quality result and never loads pretrained weights.

``--dry-run`` emits the measurement plan without importing torch so the
contract can be unit-tested on CPU-only hosts.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

H100_BF16_DENSE_TFLOPS = 989.0  # NVIDIA H100 SXM dense BF16 peak, no sparsity

# Shapes follow the from-scratch arms in experiments/architectures/*.yaml:
# 3 GDN layers per 1 full-attention layer, tied embeddings, SwiGLU 8/3 ratio.
SHAPES: dict[str, dict[str, int]] = {
    "gdn-hybrid-125m": {"layers": 12, "hidden": 768, "heads": 12, "vocab": 32000, "batch": 16},
    "gdn-hybrid-350m": {"layers": 24, "hidden": 1024, "heads": 16, "vocab": 32000, "batch": 8},
}


@dataclass(frozen=True)
class Plan:
    shape: str
    layers: int
    hidden: int
    heads: int
    vocab: int
    seq_len: int
    batch: int
    warmup_steps: int
    timed_steps: int
    params_millions: float
    flops_per_token: float


def parameter_count(layers: int, hidden: int, vocab: int) -> int:
    """Approximate non-embedding + embedding parameters for the hybrid stack."""
    attn = 4 * hidden * hidden
    mlp = 3 * hidden * (8 * hidden // 3)
    gdn = attn + 3 * hidden  # q/k/v/o projections plus gate/decay vectors
    per_layer = mlp + (gdn * 3 + attn) / 4
    return int(layers * per_layer + vocab * hidden)


def make_plan(shape: str, seq_len: int, batch: int, warmup: int, steps: int) -> Plan:
    cfg = SHAPES[shape]
    params = parameter_count(cfg["layers"], cfg["hidden"], cfg["vocab"])
    # 6ND training FLOPs per token, plus attention FLOPs for the 1-in-4 full layers.
    attn_layers = math.ceil(cfg["layers"] / 4)
    attn_flops = 12 * attn_layers * cfg["hidden"] * seq_len
    return Plan(
        shape=shape,
        layers=cfg["layers"],
        hidden=cfg["hidden"],
        heads=cfg["heads"],
        vocab=cfg["vocab"],
        seq_len=seq_len,
        batch=batch,
        warmup_steps=warmup,
        timed_steps=steps,
        params_millions=round(params / 1e6, 2),
        flops_per_token=float(6 * params + attn_flops),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shape", choices=sorted(SHAPES), default="gdn-hybrid-125m")
    parser.add_argument("--seq-len", type=int, default=2048)
    parser.add_argument("--batch", type=int, default=0, help="0 = the shape's registered batch")
    parser.add_argument(
        "--head-dim", type=int, default=0, help="0 = hidden // heads (fla default is 256)"
    )
    parser.add_argument("--expand-v", type=int, default=1)
    parser.add_argument("--warmup-steps", type=int, default=5)
    parser.add_argument("--timed-steps", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.batch == 0:
        args.batch = SHAPES[args.shape]["batch"]
    if args.head_dim == 0:
        args.head_dim = SHAPES[args.shape]["hidden"] // SHAPES[args.shape]["heads"]
    if args.seq_len < 128 or args.batch < 1 or args.timed_steps < 1 or args.expand_v < 1:
        parser.error("seq-len must be >=128; batch, timed-steps, expand-v must be >=1")
    return args


def _build_model(plan: Plan, head_dim: int, expand_v: int):  # pragma: no cover - GPU only
    import torch
    from fla.layers import GatedDeltaNet
    from torch import nn

    class Block(nn.Module):
        def __init__(self, use_attention: bool) -> None:
            super().__init__()
            self.norm1 = nn.RMSNorm(plan.hidden)
            self.norm2 = nn.RMSNorm(plan.hidden)
            if use_attention:
                self.mixer = nn.MultiheadAttention(
                    plan.hidden, plan.heads, batch_first=True, bias=False
                )
            else:
                self.mixer = GatedDeltaNet(
                    hidden_size=plan.hidden,
                    num_heads=plan.heads,
                    head_dim=head_dim,
                    expand_v=expand_v,
                    mode="chunk",
                )
            self.use_attention = use_attention
            inner = 8 * plan.hidden // 3
            self.mlp = nn.Sequential(
                nn.Linear(plan.hidden, 2 * inner, bias=False),
                nn.SiLU(),
                nn.Linear(2 * inner, plan.hidden, bias=False),
            )

        def forward(self, x):
            h = self.norm1(x)
            if self.use_attention:
                mask = torch.nn.Transformer.generate_square_subsequent_mask(
                    h.shape[1], device=h.device
                )
                h, _ = self.mixer(h, h, h, attn_mask=mask, need_weights=False)
            else:
                h = self.mixer(h)[0]
            x = x + h
            return x + self.mlp(self.norm2(x))

    class Model(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.embed = nn.Embedding(plan.vocab, plan.hidden)
            self.blocks = nn.ModuleList(
                [Block(use_attention=(i % 4 == 3)) for i in range(plan.layers)]
            )
            self.norm = nn.RMSNorm(plan.hidden)

        def forward(self, tokens):
            x = self.embed(tokens)
            for block in self.blocks:
                x = block(x)
            return self.norm(x) @ self.embed.weight.T

    return Model()


def measure(plan: Plan, head_dim: int, expand_v: int) -> dict[str, object]:  # pragma: no cover
    import torch

    if not torch.cuda.is_available():
        raise SystemExit("fla_throughput_doctor requires a CUDA device")
    device = torch.device("cuda")
    torch.manual_seed(0)
    model = _build_model(plan, head_dim, expand_v).to(device=device, dtype=torch.bfloat16)
    actual_params = sum(p.numel() for p in model.parameters())
    attention_flops = plan.flops_per_token - 6 * plan.params_millions * 1e6
    actual_flops_per_token = 6 * actual_params + attention_flops
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    tokens = torch.randint(0, plan.vocab, (plan.batch, plan.seq_len), device=device)

    def step() -> None:
        logits = model(tokens[:, :-1])
        loss = torch.nn.functional.cross_entropy(
            logits.float().reshape(-1, plan.vocab), tokens[:, 1:].reshape(-1)
        )
        loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)

    for _ in range(plan.warmup_steps):
        step()
    torch.cuda.synchronize()
    start = time.perf_counter()
    for _ in range(plan.timed_steps):
        step()
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    tokens_per_step = plan.batch * (plan.seq_len - 1)
    tokens_per_second = tokens_per_step * plan.timed_steps / elapsed
    achieved_tflops = tokens_per_second * actual_flops_per_token / 1e12
    import fla

    return {
        "mode": "eager, bf16 params, fp32 loss, no compile, no fused cross-entropy",
        "head_dim": head_dim,
        "expand_v": expand_v,
        "actual_params_millions": round(actual_params / 1e6, 2),
        "flops_per_token_used": actual_flops_per_token,
        "tokens_per_second": round(tokens_per_second, 1),
        "seconds_per_step": round(elapsed / plan.timed_steps, 4),
        "achieved_tflops": round(achieved_tflops, 2),
        "mfu_vs_h100_bf16_dense": round(achieved_tflops / H100_BF16_DENSE_TFLOPS, 4),
        "peak_memory_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "gpu_name": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "fla_version": getattr(fla, "__version__", "unknown"),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = make_plan(args.shape, args.seq_len, args.batch, args.warmup_steps, args.timed_steps)
    receipt: dict[str, object] = {
        "doctor": "fla_throughput_doctor",
        "evidence_grade": "infrastructure-only; no quality or architecture claim",
        "plan": asdict(plan),
        "python": platform.python_version(),
        "dry_run": bool(args.dry_run),
    }
    receipt["geometry"] = {"head_dim": args.head_dim, "expand_v": args.expand_v}
    if not args.dry_run:
        receipt["measurement"] = measure(plan, args.head_dim, args.expand_v)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
