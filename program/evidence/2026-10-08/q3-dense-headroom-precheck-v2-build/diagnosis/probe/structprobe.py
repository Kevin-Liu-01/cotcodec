"""Diagnostic (CPU): v1 per-unit evaluation on the real Qwen3-0.6B and Qwen3.5-4B layer structure
(real layer counts, head counts, head dims and vocabularies; hidden and MLP widths reduced so CPU
compute stays small), counting torch ops and timing each part. The gated-delta chunk kernel is
replaced by a zero-cost stand-in so that only the code around it is measured. Synthetic inputs."""
import collections
import cProfile
import io
import os
import pstats
import sys
import time
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
LENGTH = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
sys.path.insert(0, str(REPO))
OUT.mkdir(parents=True, exist_ok=True)
from harness import dense_headroom_data as dhd  # noqa: E402

dhd.block_gpu_only_kernels()
import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch.utils._python_dispatch import TorchDispatchMode  # noqa: E402

from harness import dense_headroom_stats as dhs  # noqa: E402
from harness import dense_headroom_torch as dht  # noqa: E402
from harness import sparse_indexer_torch as sit  # noqa: E402

torch.set_num_threads(16)
names = dhs.selector_names([42, 43, 44])
dev = torch.device("cpu")


class Count(TorchDispatchMode):
    def __init__(self):
        super().__init__()
        self.ops = collections.Counter()

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        self.ops[str(func.overloadpacket)] += 1
        return func(*args, **(kwargs or {}))


def build(kind):
    from transformers import (Qwen3_5ForCausalLM, Qwen3_5TextConfig, Qwen3Config,
                              Qwen3ForCausalLM)
    torch.manual_seed(0)
    if kind == "qwen3.5-4b-structure":
        cfg = Qwen3_5TextConfig(
            vocab_size=248320, hidden_size=256, intermediate_size=512, num_hidden_layers=32,
            num_attention_heads=16, num_key_value_heads=4, head_dim=256,
            linear_conv_kernel_dim=4, linear_key_head_dim=128, linear_num_key_heads=16,
            linear_num_value_heads=32, linear_value_head_dim=128,
            layer_types=["full_attention" if i % 4 == 3 else "linear_attention" for i in range(32)],
            max_position_embeddings=32768, tie_word_embeddings=True,
            rope_parameters={"rope_type": "default", "rope_theta": 1e7, "partial_rotary_factor": 0.25,
                             "mrope_interleaved": True, "mrope_section": [11, 11, 10]})
        cfg._attn_implementation = sit.CAPTURE_IMPLEMENTATION
        sit.register_capture_implementation()
        model = Qwen3_5ForCausalLM(cfg)
    else:
        cfg = Qwen3Config(vocab_size=151936, hidden_size=256, intermediate_size=512,
                          num_hidden_layers=28, num_attention_heads=16, num_key_value_heads=8,
                          head_dim=128, max_position_embeddings=32768, tie_word_embeddings=True)
        cfg._attn_implementation = sit.CAPTURE_IMPLEMENTATION
        sit.register_capture_implementation()
        model = Qwen3ForCausalLM(cfg)
    model = model.to(torch.bfloat16).eval().requires_grad_(False)
    return model


def fake_chunk(query, key, value, g, beta, chunk_size=64, initial_state=None,
               output_final_state=False, use_qk_l2norm_in_kernel=False, **kwargs):
    b, t, h, dk = key.shape
    dv = value.shape[-1]
    out = torch.zeros(b, t, value.shape[2], dv, dtype=query.dtype)
    state = torch.zeros(b, value.shape[2], dk, dv, dtype=torch.float32) if output_final_state else None
    return out, state


from transformers.models.qwen3_5 import modeling_qwen3_5 as m  # noqa: E402

m.torch_chunk_gated_delta_rule = fake_chunk
rng = np.random.default_rng(0)
for kind in ("qwen3-0.6b-structure", "qwen3.5-4b-structure"):
    model = build(kind)
    hybrid = kind.startswith("qwen3.5")
    torch.use_deterministic_algorithms(True, warn_only=hybrid)
    vocab = model.config.vocab_size
    tokens = rng.integers(3, vocab - 1, size=LENGTH + 24).astype(np.uint32)
    q0, q1, n0, n1 = LENGTH + 2, LENGTH + 20, LENGTH // 3, LENGTH // 3 + 120
    options = [rng.integers(3, vocab - 1, size=int(n)).astype(np.uint32) for n in (5, 9, 2, 12)]
    lex = np.zeros(len(tokens) // 4, dtype=np.float32)
    layers = dht.attention_layers(model.config)
    kw = dict(layers=layers, k_blocks=dhd.budget_blocks(LENGTH), fixed_k_blocks=256,
              scaling=dht.scaling_of(model.config), seeds=[42, 43, 44], unit_key="c0-q0",
              names=names, hybrid=hybrid, device=dev, options=options,
              option_bytes=[5, 9, 2, 12], answer=1, lex_blocks=lex)
    dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=True, do_mc=True, **kw)
    res = {}
    for label, sel, mc in (("select_only", True, False), ("mc_only", False, True),
                           ("both", True, True)):
        t0 = time.perf_counter()
        dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=sel, do_mc=mc, **kw)
        res[label] = round(time.perf_counter() - t0, 3)
    counter = Count()
    with counter:
        dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=True, do_mc=True, **kw)
    prof = cProfile.Profile()
    prof.enable()
    dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=True, do_mc=True, **kw)
    prof.disable()
    s = io.StringIO()
    pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(25)
    (OUT / f"struct-{kind}-L{LENGTH}.txt").write_text(s.getvalue())
    print(kind, "L", LENGTH, res, "ops/unit", sum(counter.ops.values()),
          "top", counter.ops.most_common(8), flush=True)
