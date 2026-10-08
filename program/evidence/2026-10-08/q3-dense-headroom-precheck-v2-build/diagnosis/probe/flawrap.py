"""Diagnostic (CPU): Python-side cost of fla's chunk_gated_delta_rule with every Triton launch
replaced by a no-op (outputs stay uninitialised; only the wrapper path is timed)."""
import cProfile, io, pstats, time
import torch
import triton.runtime.jit as jit
import triton.runtime.autotuner as at

launches = {"n": 0}


def fake_run(self, *args, grid=None, warmup=False, **kwargs):
    launches["n"] += 1
    return None


def fake_autotune_run(self, *args, **kwargs):
    self.nargs = dict(zip(self.arg_names, args))
    config = self.configs[0]
    out = self.fn.run(*args, **kwargs, **config.all_kwargs())
    self.nargs = None
    return out


jit.JITFunction.run = fake_run
at.Autotuner.run = fake_autotune_run
from fla.ops.gated_delta_rule import chunk_gated_delta_rule  # noqa: E402

for T in (8, 6000):
    q = torch.randn(1, T, 32, 128, dtype=torch.bfloat16)
    k = torch.randn(1, T, 32, 128, dtype=torch.bfloat16)
    v = torch.randn(1, T, 32, 128, dtype=torch.bfloat16)
    g = -torch.rand(1, T, 32)
    beta = torch.rand(1, T, 32, dtype=torch.bfloat16)
    h0 = torch.zeros(1, 32, 128, 128)
    with torch.no_grad():
        chunk_gated_delta_rule(q, k, v, g=g, beta=beta, initial_state=h0, output_final_state=True,
                               use_qk_l2norm_in_kernel=True)
        launches["n"] = 0
        n = 50
        prof = cProfile.Profile()
        t0 = time.perf_counter()
        prof.enable()
        for _ in range(n):
            chunk_gated_delta_rule(q, k, v, g=g, beta=beta, initial_state=h0,
                                   output_final_state=True, use_qk_l2norm_in_kernel=True)
        prof.disable()
        dt = (time.perf_counter() - t0) / n
    print(f"T={T}: {dt * 1e3:.2f} ms per call, {launches['n'] / n:.0f} launches per call", flush=True)
s = io.StringIO()
pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(15)
print(s.getvalue()[:4000])
