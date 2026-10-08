"""Q1 audit-metric study (D41 ii): CPU recomputation on S1-cal problems only.

For one S1-cal problem and its registered audit draws (A1 native draws, A2 value
distributions, A3 held-out shapes, replicate 42), this script rebuilds on the CPU
exactly the reference and inputs the audit used (``harness.q1.audit.run``'s draw
plan, the reference built as ``run.prepare`` builds it) and computes, with no
GPU and no candidate kernel:

* the fp64 oracle ``r64`` (the registered A1 oracle, run on the CPU);
* *correct* reduced-precision realizations of the same reference: CPU fp32
  (NNPACK off, direct summation), CPU fp32 with NNPACK on (Winograd for 3x3
  convolutions, a different legitimate algorithm), and TF32 emulations of the
  matmul/convolution (operands rounded RNE as cuBLAS/cuDNN do, truncated as
  Triton's ``tl.dot`` does, and stochastically rounded) with fp32 accumulation;
* *destroyed* outputs: all-zeros, negation, constant mean, a shuffled reference,
  and emulations of the registered mutant families (bias sign flip for
  ``plus2minus``, last reduction element dropped for ``mask-bound-minus1`` and
  ``loop-bound-minus1``, input read one element late for ``load-offset-off1``, a
  missing output tile and a missing last row for the boundary family, fp16
  accumulation for ``acc-fp16``, an fp16 round trip for ``store-fp16``, output
  gains of 1e-2, 1e-3 and 1e-4 for the constant-perturbation and
  ``store-scale-nudge`` operators, sparse single-element and 0.1% faults);
* a first-order error gauge ``Delta`` (BLAS dblat3 / Higham style): the
  magnitude ``G = |W| |x| + |b|`` of the linear stage, scaled by the unit
  roundoff (2^-11 under TF32; 2^-24 sqrt(K) under strict fp32), propagated through the problem's post-ops (elementwise ops by
  interval endpoints, pooling by the same nonnegative average, batch and group
  norm by the first-order bound on ``|J|``);
* every candidate metric's statistics for each output against ``r64``, under
  three yardsticks (strict fp32; the registered TF32-admissible set, fp32 and
  TF32-RNE; and an extended TF32 set that adds TF32-RZ).

The draw plan, inputs and weights come from the frozen harness code; inputs drawn
by ``torch.rand`` reproduce the GPU jobs' inputs bitwise (checked against job
752's stored input fingerprints by ``check_fingerprints``). Nothing here runs a
candidate kernel or touches an evaluation unit: ``PROBLEMS`` lists S1-cal
problems with no S2 substrate only, and the script refuses any other problem.

Usage: python cpu_study.py L2/46 --channels A1,A2,A3 --out cpu/
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from harness.q1 import problems as problem_lib  # noqa: E402
from harness.q1 import refstore  # noqa: E402
from harness.q1.audit import run as audit_run  # noqa: E402
from harness.q1.audit.oracle import KAPPA  # noqa: E402
from harness.q1.gates.common import first_tensor_outputs, process_inputs  # noqa: E402
from harness.q1.substrates import s2_catalog  # noqa: E402
from tf32emu import TF32Mode  # noqa: E402

aten = torch.ops.aten
U_TF32 = 2.0**-11
U_FP32 = 2.0**-24
BLOCK = 4096
REPLICATE = 42
CPU = torch.device("cpu")

# --- the problems: S1-cal, no S2 substrate (D28) -------------------------------------
# Post-op chains after the captured linear op, as the reference's forward computes
# them. Steps: ("ew", f) elementwise; ("affine", a, c) z*a + c with a, c constants;
# ("param", name) z + module parameter (broadcast on the last dim); ("tril",);
# ("pool", f) a nonnegative linear pooling; ("bn", eps) training-mode batch norm with
# unit weight and zero bias; ("gn", groups, eps) group norm likewise.


def _swish(z: torch.Tensor) -> torch.Tensor:
    return torch.sigmoid(z) * z


def _gelu(z: torch.Tensor) -> torch.Tensor:
    return F.gelu(z)


POST: dict[str, list[tuple]] = {
    "L1/10": [],
    "L1/18": [],
    "L1/15": [("tril",)],
    "L1/47": [],
    "L2/59": [("ew", _swish), ("affine", 2.0, 0.0)],
    "L2/95": [
        ("param", "add_value"),
        ("ew", _swish),
        ("ew", torch.tanh),
        ("ew", _gelu),
        ("ew", lambda z: F.hardtanh(z, -1.0, 1.0)),
    ],
    "L2/77": [("affine", 2.0, 0.0), ("bn", 1e-5), ("pool", lambda z: F.adaptive_avg_pool3d(z, 1))],
    "L2/100": [("ew", lambda z: torch.clamp(z, min=-1.0)), ("affine", 0.5, 0.0)],
    "L2/87": [("affine", 1.0, -0.5), ("affine", 1.0, -0.2), ("ew", F.mish)],
    "L2/46": [
        ("affine", 1.0, -0.5),
        ("ew", torch.tanh),
        ("affine", 1.0, -0.2),
        ("pool", lambda z: F.avg_pool2d(z, 2)),
    ],
    "L2/52": [("ew", lambda z: torch.tanh(F.softplus(z)) * z), ("bn", 1e-5)],
    "L2/60": [("ew", _swish), ("gn", 4, 1e-5), ("ew", F.hardswish)],
}
PROBLEMS = tuple(POST)
#: problems where a full extra forward per draw is expensive on this CPU (s per pass)
HEAVY = {"L2/77", "L2/100", "L2/87", "L2/46", "L2/52", "L2/60"}
#: batch-independent problems (convolution and per-sample ops, no batch norm): the only
#: ones ``--batch-subset`` may slice. Inputs are drawn at full batch exactly as the audit
#: drew them and then sliced, so every output is the exact leading slice of the
#: registered draw's output (max-type statistics over a slice can only be smaller).
BATCH_INDEPENDENT = {"L1/10", "L2/100", "L2/87", "L2/60", "L2/46", "L2/95", "L2/59"}
LINEAR_OPS = {
    aten.mm.default,
    aten.bmm.default,
    aten.addmm.default,
    aten.convolution.default,
    aten.sum.dim_IntList,
}


def full_problem_id(short: str) -> str:
    ids = [p for p in problem_lib.list_problem_ids(include_excluded=True) if p.split("_")[0] == short]
    if len(ids) != 1:
        raise SystemExit(f"no unique problem for {short}")
    return ids[0]


def assert_non_evaluation(problem_id: str) -> dict[str, Any]:
    """D28: refuse anything but an S1-cal problem with no S2 (evaluation) substrate."""
    from harness.q1 import analysis

    split = analysis.s1_split()
    s2_problems = {e.problem_id for e in s2_catalog.CATALOG}
    if problem_id not in split["calibration"]:
        raise SystemExit(f"{problem_id} is not in S1-cal: refused (D28)")
    if problem_id in s2_problems:
        raise SystemExit(f"{problem_id} hosts an S2 evaluation substrate: refused (D28)")
    return {"s1_half": "calibration", "split_sha256": split["sha256"], "hosts_s2": False}


# --- capture of the linear stage ------------------------------------------------------


class Capture(torch.utils._python_dispatch.TorchDispatchMode):
    """Records the first linear op (matmul, convolution or the reduction) of a forward."""

    def __init__(self) -> None:
        super().__init__()
        self.func = None
        self.args: Any = None
        self.kwargs: Any = None
        self.out: torch.Tensor | None = None

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        out = func(*args, **(kwargs or {}))
        if self.func is None and func in LINEAR_OPS:
            self.func, self.args, self.kwargs, self.out = func, args, kwargs or {}, out
        return out


def _abs_args(args: Any) -> list[Any]:
    return [a.abs() if isinstance(a, torch.Tensor) and a.is_floating_point() else a for a in args]


def linear_gauge(cap: Capture) -> torch.Tensor:
    """G = the linear op on absolute operands (|W||x| + |b|), in fp64."""
    args = [a.double() if isinstance(a, torch.Tensor) and a.is_floating_point() else a for a in cap.args]
    with torch.no_grad():
        return cap.func(*_abs_args(args), **cap.kwargs)


def reduction_length(cap: Capture) -> int:
    f, a = cap.func, cap.args
    if f in (aten.mm.default, aten.bmm.default):
        return int(a[0].shape[-1])
    if f == aten.addmm.default:
        return int(a[1].shape[-1])
    if f == aten.convolution.default:
        w, transposed = a[1], a[6]
        k = int(math.prod(w.shape[2:]))
        if transposed:
            stride = int(math.prod(a[3]))
            return int(w.shape[0]) * max(1, k // stride)
        return int(w.shape[1]) * k
    if f == aten.sum.dim_IntList:
        return int(math.prod(a[0].shape[d] for d in a[1]))
    raise ValueError(f)


def drop_last_k(cap: Capture) -> torch.Tensor:
    """Linear-stage output with the last reduction element dropped (fp64)."""
    f, a = cap.func, [x.double() if isinstance(x, torch.Tensor) and x.is_floating_point() else x for x in cap.args]
    z = cap.out.double()
    if f == aten.mm.default:
        return z - a[0][:, -1:] @ a[1][-1:, :]
    if f == aten.bmm.default:
        return z - a[0][..., -1:] @ a[1][..., -1:, :]
    if f == aten.addmm.default:
        return z - a[1][:, -1:] @ a[2][-1:, :]
    if f == aten.convolution.default:
        x, w = a[0], a[1]
        rest = list(a[3:8]) + [1]
        ws = w[-1:] if a[6] else w[:, -1:]
        return z - aten.convolution.default(x[:, -1:], ws, None, *rest)
    if f == aten.sum.dim_IntList:
        x, dims = a[0], a[1]
        keep = a[2] if len(a) > 2 else cap.kwargs.get("keepdim", False)
        last = x.narrow(dims[-1], x.shape[dims[-1]] - 1, 1)
        return z - (last if keep else last.squeeze(dims[-1]))
    raise ValueError(f)


def bias_sign(cap: Capture) -> torch.Tensor | None:
    """Linear-stage output with the bias added with the wrong sign (plus2minus)."""
    f, a = cap.func, cap.args
    z = cap.out.double()
    if f == aten.addmm.default:
        return z - 2.0 * a[0].double()
    if f == aten.convolution.default and a[2] is not None:
        b = a[2].double().view(1, -1, *([1] * (z.dim() - 2)))
        return z - 2.0 * b
    return None


def acc_fp16(cap: Capture, block_k: int = 32) -> torch.Tensor | None:
    """acc-fp16: an fp16 accumulator over BLOCK_K chunks of fp32 dot products."""
    f, a = cap.func, cap.args
    if f == aten.mm.default:
        lhs, rhs, bias = a[0], a[1], None
    elif f == aten.addmm.default:
        bias, lhs, rhs = a[0], a[1], a[2]
    else:
        return None
    k = lhs.shape[-1]
    acc = torch.zeros(lhs.shape[0], rhs.shape[1], dtype=torch.float16)
    with torch.no_grad():
        for s in range(0, k, block_k):
            part = (lhs[:, s : s + block_k].float() @ rhs[s : s + block_k].float()).half()
            acc = (acc.float() + part.float()).half()
        out = acc.float()
        if bias is not None:
            out = out + bias.float()
    return out.double()


# --- post-op chain, its bound propagation, and checks --------------------------------


def apply_post(problem: str, z: torch.Tensor, model: torch.nn.Module, out_shape: torch.Size) -> torch.Tensor:
    for step in POST[problem]:
        kind = step[0]
        if kind == "ew":
            z = step[1](z)
        elif kind == "affine":
            z = z * step[1] + step[2]
        elif kind == "param":
            z = z + getattr(model, step[1]).to(z.dtype)
        elif kind == "tril":
            z = torch.tril(z)
        elif kind == "pool":
            z = step[1](z)
        elif kind == "bn":
            z = F.batch_norm(z, None, None, training=True, eps=step[1])
        elif kind == "gn":
            z = F.group_norm(z, step[1], eps=step[2])
        else:
            raise ValueError(kind)
    return z.reshape(out_shape)


def _norm_bound(z: torch.Tensor, b: torch.Tensor, dims: tuple[int, ...], eps: float) -> torch.Tensor:
    mu = z.mean(dim=dims, keepdim=True)
    var = z.var(dim=dims, keepdim=True, unbiased=False)
    s = torch.sqrt(var + eps)
    zh = (z - mu) / s
    return (b + b.mean(dim=dims, keepdim=True) + zh.abs() * (zh.abs() * b).mean(dim=dims, keepdim=True)) / s


def propagate_bound(problem: str, z: torch.Tensor, b: torch.Tensor, model: torch.nn.Module, out_shape: torch.Size) -> torch.Tensor:
    """First-order bound on |output error| given |linear-stage error| <= b (fp64)."""
    for step in POST[problem]:
        kind = step[0]
        if kind == "ew":
            f = step[1]
            fz = f(z)
            b = torch.maximum((f(z + b) - fz).abs(), (f(z - b) - fz).abs())
            z = fz
        elif kind == "affine":
            b = b * abs(step[1])
            z = z * step[1] + step[2]
        elif kind == "param":
            z = z + getattr(model, step[1]).to(z.dtype)
        elif kind == "tril":
            z, b = torch.tril(z), torch.tril(b)
        elif kind == "pool":
            z, b = step[1](z), step[1](b)
        elif kind == "bn":
            dims = (0, *range(2, z.dim()))
            b = _norm_bound(z, b, dims, step[1])
            z = F.batch_norm(z, None, None, training=True, eps=step[1])
        elif kind == "gn":
            n, c = z.shape[:2]
            g = step[1]
            zg = z.reshape(n, g, -1)
            bg = _norm_bound(zg, b.reshape(n, g, -1), (2,), step[2])
            b = bg.reshape(z.shape)
            z = F.group_norm(z, g, eps=step[2])
        else:
            raise ValueError(kind)
    return b.reshape(out_shape)


# --- statistics (chunked: outputs reach 868M elements) --------------------------------

CHUNK = 1 << 24  # a multiple of BLOCK


def _chunks(n: int):
    for s in range(0, n, CHUNK):
        yield s, min(n, s + CHUNK)


class Denominators:
    """Per-draw reciprocal denominators shared by every output's statistics (fp32):
    the registered metric's ``|r| + kappa ||r||_inf``, the gauges ``D``, and M6's
    ``|r| + D``. The oracle ``r`` is finite on every studied draw."""

    def __init__(self, r: torch.Tensor, rinf: float, gauges: dict[str, torch.Tensor]) -> None:
        if not bool(torch.isfinite(r).all()):
            raise ValueError("non-finite oracle output")
        ra = r.reshape(-1).abs()
        self.inv = {"reg": (1.0 / (ra + KAPPA * rinf)).float()}
        for k, g in gauges.items():
            gd = g.reshape(-1).double()
            self.inv[f"m3_{k}"] = (1.0 / gd).float()
            self.inv[f"m6_{k}"] = (1.0 / (ra + gd)).float()
        self.rr = float((ra * ra).sum())
        self.keys = list(gauges)


def stats(x: torch.Tensor, r: torch.Tensor, dens: Denominators) -> tuple[dict[str, Any], torch.Tensor]:
    """Every metric's raw statistic for output ``x`` against the oracle ``r``, and the
    per-block squared error (blocks of ``BLOCK`` consecutive elements)."""
    xf, rf = x.reshape(-1), r.reshape(-1)
    n = rf.numel()
    mx = {k: 0.0 for k in dens.inv}
    sq = linf = xr = xx = 0.0
    finite = True
    blocks = []
    for s, e in _chunks(n):
        xd = xf[s:e].double()
        rd = rf[s:e]
        d64 = (xd - rd).abs()
        if not bool(torch.isfinite(xd).all()):
            finite = False
            d64 = torch.nan_to_num(d64, nan=math.inf)
        d = d64.float()
        for k, inv in dens.inv.items():
            q = d * inv[s:e]
            q = torch.where(d == 0, torch.zeros_like(q), q)
            mx[k] = max(mx[k], float(q.max()))
        dd = d64 * d64
        sq += float(dd.sum())
        linf = max(linf, float(d64.max()))
        if finite:
            xr += float((xd * rd).sum())
            xx += float((xd * xd).sum())
        pad = (-dd.numel()) % BLOCK
        if pad:
            dd = torch.cat([dd, dd.new_zeros(pad)])
        blocks.append(dd.reshape(-1, BLOCK).sum(dim=1))
    out: dict[str, Any] = {
        "finite": finite,
        "e_reg": mx["reg"] if finite else math.inf,
        "l2": math.sqrt(sq),
        "linf": linf,
    }
    for k in dens.keys:
        out[f"m3_{k}"] = mx[f"m3_{k}"]
        out[f"m6_{k}"] = mx[f"m6_{k}"]
    rr = dens.rr
    out["gain"] = xr / rr if rr > 0 and finite else math.nan
    out["one_minus_cos"] = 1.0 - xr / math.sqrt(xx * rr) if finite and xx > 0 and rr > 0 else math.nan
    return out, torch.cat(blocks)


# --- decoys from the oracle (built one at a time) --------------------------------------


def oracle_decoys(r: torch.Tensor, seed: int) -> dict[str, Any]:
    n = r.numel()
    flat = r.reshape(-1)
    rms = float(torch.sqrt((flat * flat).mean()))
    mean = float(flat.mean())

    def shuffled() -> torch.Tensor:
        g = torch.Generator().manual_seed(seed)
        return flat[torch.randperm(n, generator=g)].reshape(r.shape)

    def noise() -> torch.Tensor:
        g = torch.Generator().manual_seed(seed + 1)
        return r + 1e-2 * rms * torch.randn(r.shape, generator=g, dtype=r.dtype)

    def tile() -> torch.Tensor:
        t = flat.clone()
        t[n - max(1, n // 64) :] = 0
        return t.reshape(r.shape)

    def last_row() -> torch.Tensor:
        t = r.clone()
        if r.dim() >= 2 and r.shape[-2] > 1:
            dim = r.dim() - 2
        elif r.dim() > 1 and r.shape[1] > 1:
            dim = 1
        else:
            dim = 0
        t.select(dim, r.shape[dim] - 1).zero_()
        return t

    def single() -> torch.Tensor:
        t = flat.clone()
        t[int(flat.abs().argmax())] = 0
        return t.reshape(r.shape)

    def sparse() -> torch.Tensor:
        g = torch.Generator().manual_seed(seed + 2)
        t = flat.clone()
        t[torch.randperm(n, generator=g)[: max(1, n // 1000)]] = 0
        return t.reshape(r.shape)

    return {
        "zeros": lambda: torch.zeros_like(r),
        "negation": lambda: -r,
        "constant_mean": lambda: torch.full_like(r, mean),
        "shuffled": shuffled,
        "gain_1e-2": lambda: r * (1 + 1e-2),
        "gain_1e-3": lambda: r * (1 + 1e-3),
        "store_scale_nudge_1e-4": lambda: r * 0.9999,
        "noise_1e-2": noise,
        "store_fp16": lambda: r.float().half().double(),
        "tile_missing_1of64": tile,
        "last_row_zero": last_row,
        "single_max_zeroed": single,
        "sparse_1e-3_zeroed": sparse,
    }


# --- one draw --------------------------------------------------------------------------

YARDSTICKS = {"strict": ["fp32"], "tf32_reg": ["fp32", "tf32_rne"], "tf32_ext": ["fp32", "tf32_rne", "tf32_rz"]}


def run_draw(problem: str, ref: torch.nn.Module, inputs: list[Any], *, seed: int, extra_forwards: bool, conv2d: bool) -> dict[str, Any]:
    t0 = time.time()
    timings: dict[str, float] = {}
    dbl = [x.double() if isinstance(x, torch.Tensor) and x.is_floating_point() else x for x in inputs]
    with torch.no_grad():
        oracle = copy.deepcopy(ref).double()
        cap = Capture()
        with cap:
            r = first_tensor_outputs(oracle(*dbl))[0].detach()
        timings["oracle_fp64"] = time.time() - t0
        rinf = float(r.abs().max())
        rnorm = float(torch.linalg.vector_norm(r))
        z64 = cap.out.double()
        chain_err = float((apply_post(problem, z64, oracle, r.shape) - r).abs().max())

        # gauge (fp64), then kept as fp32 denominators
        t = time.time()
        G = linear_gauge(cap)
        K = reduction_length(cap)
        zabs = z64.abs().reshape(-1)
        c = zabs / G.reshape(-1).clamp_min(1e-300)
        samp = c[:: max(1, c.numel() // 2_000_000)]
        cond_lin = {
            "linear_cancellation_q": {str(q): float(torch.quantile(samp, q)) for q in (0.001, 0.01, 0.1, 0.5)},
            "linear_cancellation_min": float(c.min()),
            "G_inf_over_z_inf": float(G.max() / zabs.max()) if float(zabs.max()) > 0 else math.inf,
        }
        del c, samp, zabs
        delta_t = propagate_bound(problem, z64, U_TF32 * G, oracle, r.shape)
        gauges = {"t": (delta_t + U_FP32 * r.abs()).float().clamp_min(1e-30)}
        dt_stats = {
            "delta_t_inf_over_r_inf": float(delta_t.max()) / rinf if rinf > 0 else math.inf,
            "delta_t_rms_over_r_rms": float(torch.linalg.vector_norm(delta_t)) / max(1e-300, rnorm),
        }
        dflat_t = delta_t.reshape(-1)
        del delta_t
        # strict fp32: products and accumulation both round in fp32, so the gauge's unit
        # is u32 * sqrt(K) (blocked or pairwise accumulation; dblat3's eps * G is for K ~ 1)
        delta_s = propagate_bound(problem, z64, U_FP32 * math.sqrt(K) * G, oracle, r.shape)
        gauges["s"] = (delta_s + U_FP32 * r.abs()).float().clamp_min(1e-30)
        del delta_s, G
        dens = Denominators(r, rinf, gauges)
        del gauges
        timings["gauge"] = time.time() - t

        def fwd(mode: str | None, nnpack: bool = False, seed_sr: int = 0) -> torch.Tensor:
            t = time.time()
            torch.backends.nnpack.set_flags(nnpack)
            try:
                m = copy.deepcopy(ref)
                if mode is None:
                    out = first_tensor_outputs(m(*inputs))[0].detach()
                else:
                    with TF32Mode(mode, seed=seed_sr):
                        out = first_tensor_outputs(m(*inputs))[0].detach()
            finally:
                torch.backends.nnpack.set_flags(False)
            timings[f"fwd_{mode or 'fp32'}{'_nnpack' if nnpack else ''}"] = time.time() - t
            return out

        rec_out: dict[str, Any] = {"correct": {}, "destroyed": {}}
        bsq: dict[str, torch.Tensor] = {}
        correct_modes = [("fp32", None, False), ("tf32_rne", "rne", False), ("tf32_rz", "rz", False), ("tf32_sr", "sr", False)]
        if conv2d:
            correct_modes.append(("fp32_nnpack", None, True))
        reg_anatomy = None
        for name, mode, nn in correct_modes:
            x = fwd(mode, nnpack=nn, seed_sr=seed)
            rec_out["correct"][name], bsq[name] = stats(x, r, dens)
            if name == "tf32_rne":
                d = (x.double() - r).abs().reshape(-1)
                den = r.abs().reshape(-1) + KAPPA * rinf
                imax = int((d / den).argmax())
                reg_anatomy = {
                    "abs_err": float(d[imax]),
                    "abs_r": float(r.reshape(-1)[imax].abs()),
                    "kappa_rinf": KAPPA * rinf,
                    "delta_t": float(dflat_t[imax]),
                    "abs_err_over_delta_t": float(d[imax] / dflat_t[imax]) if float(dflat_t[imax]) > 0 else math.inf,
                }
                del d, den
            del x

        nb = {y: torch.stack([bsq[m] for m in members]).max(dim=0).values for y, members in YARDSTICKS.items()}
        m2: dict[str, dict[str, Any]] = {y: {"rms_block_noise_l2": float(torch.sqrt(v.mean()))} for y, v in nb.items()}

        def m2_ratios(group: str, name: str, xb: torch.Tensor) -> None:
            for y, v in nb.items():
                rms = float(torch.sqrt(v.mean()))
                for phi in (0.25, 1.0):
                    floor = torch.clamp(v, min=(phi * rms) ** 2 if rms > 0 else 1e-300)
                    m2[y].setdefault(group, {}).setdefault(name, {})[f"phi_{phi}"] = float(torch.sqrt(xb / floor).max())

        for name, xb in bsq.items():
            m2_ratios("correct", name, xb)

        destroyed = oracle_decoys(r, seed)
        destroyed["drop_last_k"] = lambda: apply_post(problem, drop_last_k(cap), oracle, r.shape)
        if bias_sign(cap) is not None:
            destroyed["bias_sign"] = lambda: apply_post(problem, bias_sign(cap), oracle, r.shape)
        if problem == "L2/95":
            def addv() -> torch.Tensor:
                m2_ = copy.deepcopy(oracle)
                m2_.add_value.data = -m2_.add_value.data
                return apply_post(problem, z64, m2_, r.shape)
            destroyed["add_value_sign"] = addv
        if cap.func in (aten.mm.default, aten.addmm.default):
            destroyed["acc_fp16"] = lambda: apply_post(problem, acc_fp16(cap), oracle, r.shape)
        if extra_forwards:
            def shifted() -> torch.Tensor:
                t = time.time()
                x0 = inputs[0]
                sx = torch.cat([x0.reshape(-1)[1:], x0.new_zeros(1)]).reshape(x0.shape)
                o = first_tensor_outputs(copy.deepcopy(ref)(sx, *inputs[1:]))[0].detach()
                timings["fwd_shift"] = time.time() - t
                return o
            destroyed["load_offset_off1"] = shifted
        t = time.time()
        for name, make in destroyed.items():
            x = make()
            rec_out["destroyed"][name], xb = stats(x, r, dens)
            m2_ratios("destroyed", name, xb)
            del x, xb
        rec_out["m2"] = m2
        timings["destroyed_and_stats"] = time.time() - t

        lin_args = [a for a in cap.args if isinstance(a, torch.Tensor) and a.is_floating_point()]
        cond = {
            "numel": r.numel(),
            "reduction_length": K,
            "linear_op": str(cap.func),
            "input_negative_fraction": float((inputs[0] < 0).double().mean()),
            "operand_negative_fractions": [float((a < 0).double().mean()) for a in lin_args[:3]],
            **cond_lin,
            **dt_stats,
            "r_inf": rinf,
            "r_l2": rnorm,
            "frac_r_below_kappa_rinf": float((r.abs() < KAPPA * rinf).double().mean()),
            "reg_argmax_rne": reg_anatomy,
            "chain_reproduces_module_max_abs": chain_err,
            "relative_l2_error": {k: v["l2"] / rnorm for k, v in rec_out["correct"].items()},
        }
    timings["total"] = time.time() - t0
    return {"out": rec_out, "conditioning": cond, "timings": timings}


def metamorphic_scaling(ref: torch.nn.Module, inputs: list[Any]) -> dict[str, Any]:
    """f(2A, B) == 2 f(A, B) bitwise (pure matmul problems), per precision mode."""
    res = {}
    with torch.no_grad():
        for mode in (None, "rne", "rz"):
            def f(xs: list[Any]) -> torch.Tensor:
                m = copy.deepcopy(ref)
                if mode is None:
                    return first_tensor_outputs(m(*xs))[0]
                with TF32Mode(mode):
                    return first_tensor_outputs(m(*xs))[0]
            a = f(inputs)
            b = f([inputs[0] * 2, *inputs[1:]])
            res[mode or "fp32"] = bool(torch.equal(b, a * 2))
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("problem")
    ap.add_argument("--channels", default="A1,A2,A3")
    ap.add_argument("--skip", default="", help="config ids (e.g. A3/inner137) to skip, comma-separated")
    ap.add_argument("--only", default="", help="draw indices per channel, e.g. A1:0,1;A2:0")
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--batch-subset", type=int, default=0, help="evaluate the first N samples (batch-independent problems only)")
    ap.add_argument("--out", default=str(HERE / "cpu"))
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    torch.backends.nnpack.set_flags(False)
    short = a.problem
    if short not in PROBLEMS:
        raise SystemExit(f"{short} is not one of the study's S1-cal problems {PROBLEMS}")
    pid = full_problem_id(short)
    guard = assert_non_evaluation(pid)
    src = problem_lib.load_problem_source(pid)
    manifest = json.loads((REPO / "harness/q1/data/shape_manifest.json").read_text())["problems"]
    ref, get_inputs = audit_run._reference_module(src, REPLICATE, CPU)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    skip = {s for s in a.skip.split(",") if s}
    only: dict[str, set[int]] = {}
    for part in filter(None, a.only.split(";")):
        ch, idx = part.split(":")
        only[ch] = {int(i) for i in idx.split(",")}
    conv2d = short in ("L2/46", "L2/87", "L2/52")
    for channel in a.channels.split(","):
        plan = audit_run._draw_plan(channel, pid, src, REPLICATE, get_inputs, manifest.get(pid))
        for index, draw in enumerate(plan):
            cfg = draw["config_id"]
            base = "/".join(cfg.split("/")[:2])
            if base in skip or (channel in only and index not in only[channel]):
                continue
            path = out_dir / f"{short.replace('/', '-')}__{cfg.replace('/', '_')}.json"
            if path.exists():
                print("exists", path.name, flush=True)
                continue
            inputs = process_inputs(draw["raw"](), CPU, "preserve")
            fp = refstore.fingerprint(inputs)
            full_batch = int(inputs[0].shape[0])
            subset = a.batch_subset or None
            if subset is not None and short not in BATCH_INDEPENDENT:
                raise SystemExit(f"{short} couples the batch (batch or group statistics); no subset")
            if subset is not None and full_batch > subset:
                inputs = [inputs[0][:subset].contiguous(), *inputs[1:]]
            extra = short not in HEAVY or index == 0
            print("run", short, cfg, flush=True)
            res = run_draw(short, ref, inputs, seed=int(draw["facts"]["seed"]), extra_forwards=extra, conv2d=conv2d and inputs[0].shape[0] >= 16)
            if short in ("L1/10", "L1/18", "L1/15") and channel == "A1" and index == 0:
                res["metamorphic_pow2_scaling_bitwise"] = metamorphic_scaling(ref, inputs)
            rec = {
                "schema": "q1-audit-metric-study/cpu-draw/1",
                "problem_id": pid,
                "problem": short,
                "channel": channel,
                "config_id": cfg,
                "facts": {k: v for k, v in draw["facts"].items()},
                "inputs_fingerprint": fp,
                "batch": {"full": full_batch, "evaluated": int(inputs[0].shape[0])},
                "guard": guard,
                "env": {
                    "torch": torch.__version__,
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "threads": torch.get_num_threads(),
                    "nnpack_for_fp32_reference": False,
                },
                "code_sha256": {
                    n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in ("cpu_study.py", "tf32emu.py")
                },
                **res,
            }
            path.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float))
            print("done", short, cfg, "%.1fs" % res["timings"]["total"], flush=True)


if __name__ == "__main__":
    main()
