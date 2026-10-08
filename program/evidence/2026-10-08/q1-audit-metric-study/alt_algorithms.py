"""Q1 audit-metric study, revision 2: valid alternative algorithms (CPU, S1-cal tier-1 only).

The first pass held out only stochastic rounding and NNPACK as correct realizations
that are not yardstick members. Both reviews showed that this false-reject test was
nearly empty: NNPACK is more accurate than the yardstick, and the TF32 RNE and RZ
realizations are themselves yardstick members. This script rebuilds registered draws
exactly as ``cpu_study.py`` does and computes correct outputs of algorithms that a
real correct kernel may use, none of which is a yardstick member:

* ``kblock_fp32``: fp32 operands; the reduction split into blocks accumulated
  sequentially in fp32 (a Triton or Inductor template K-loop with the bias in the
  epilogue). Matmuls: K blocks of 32. Convolutions: input-channel blocks (8 blocks,
  or one channel per block below 8 channels). The L1/47 sum: rows of the reduced
  dimension, one at a time (``seq1``, a single sequential accumulator) or in tiles of
  32 then sequentially (``kblock32``);
* ``kblock_tf32_rz`` and ``kblock_tf32_rne``: the same with operands rounded to TF32
  (truncation is what Triton's ``tl.dot`` does to fp32 operands);
* ``wino23`` and ``wino43``: Winograd F(2x2,3x3) and F(4x4,3x3) convolutions, with
  fp32 transforms and GEMM (``_fp32``) or with the transformed GEMM operands rounded
  to TF32 RNE (``_tf32``), on the 3x3 stride-1 convolutions (L2/46, L2/87, L2/52);
* ``tf32_sr_s<seed>``: stochastic TF32 rounding with further seeds (seed sensitivity
  of the in-sample thresholds).

Every output is scored against the study's yardsticks (strict: CPU fp32; TF32 RNE:
fp32 and TF32-RNE; TF32 extended: also TF32-RZ), as ``rho_inf`` and ``rho_block``
(phi 1, blocks of 4096) with and without the absolute floor of rule
``q1-audit-metric/2`` (2^-24 times the oracle's max-abs, and times its rms block
norm), together with the registered ``e/T`` and the oracle decoy battery on the same
draw.

D28: ``cpu_study.assert_non_evaluation`` refuses any problem outside S1-cal or
hosting an S2 substrate. No GPU, no candidate kernel.

Usage: python alt_algorithms.py L2/46 --out alt/
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
from torch.utils._python_dispatch import TorchDispatchMode

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cpu_study as cs  # noqa: E402  (also puts the repository on sys.path)
from harness.q1.audit import run as audit_run  # noqa: E402
from harness.q1.gates.common import first_tensor_outputs, process_inputs  # noqa: E402
from tf32emu import TF32Mode, round_tf32  # noqa: E402

aten = torch.ops.aten
BLOCK = 4096
FLOOR_REL = 2.0**-24
KAPPA = 1e-3
MULT = 16
T_FLOOR = 2.0**-20
YARDSTICKS = {"strict": ["fp32"], "tf32_rne": ["fp32", "tf32_rne"], "tf32_ext": ["fp32", "tf32_rne", "tf32_rz"]}

#: draws per problem (indices into the registered plan, as run_cpu_study.sh numbers them)
#: and the leading batch slice for batch-independent problems
LIGHT = {"A1": [0, 1], "A2": [0, 1, 3, 4, 6], "A3": [1, 2, 4]}
PLAN: dict[str, tuple[dict[str, list[int]], int]] = {
    "L1/10": (LIGHT, 0),
    "L1/15": (LIGHT, 0),
    "L1/18": (LIGHT, 0),
    "L2/95": (LIGHT, 0),
    "L2/46": (LIGHT, 32),
    "L2/87": (LIGHT, 32),
    "L2/60": (LIGHT, 32),
    "L1/47": ({"A1": [0, 1, 2]}, 8),
    "L2/59": ({"A1": [0], "A2": [1, 3], "A3": [1]}, 0),
    "L2/77": ({"A1": [0], "A2": [1], "A3": [2]}, 0),
    "L2/52": ({"A1": [0], "A2": [1, 3], "A3": [2]}, 0),
    "L2/100": ({"A1": [0], "A2": [1, 3], "A3": [2]}, 4),
}
#: the L1/47 sum is independent per (sample, column), so a leading slice is exact
SLICEABLE = set(cs.BATCH_INDEPENDENT) | {"L1/47"}
WINOGRAD = {"L2/46", "L2/87", "L2/52"}
SR_SEEDS = (101, 102, 103, 104)
SR_PROBLEMS = {"L1/10", "L1/15", "L1/18", "L2/95", "L2/46", "L2/87", "L2/60"}


# --- alternative algorithms ------------------------------------------------------------


class KBlockMode(TorchDispatchMode):
    """Sequential fp32 accumulation over reduction blocks, operands optionally TF32-rounded."""

    def __init__(self, bk: int, rounding: str | None = None) -> None:
        super().__init__()
        self.bk, self.rounding = bk, rounding
        self.calls = 0

    def _r(self, t: torch.Tensor) -> torch.Tensor:
        return round_tf32(t.contiguous(), self.rounding) if self.rounding else t

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        kwargs = kwargs or {}
        if func in (aten.mm.default, aten.addmm.default, aten.bmm.default):
            if func == aten.addmm.default:
                assert kwargs.get("beta", 1) == 1 and kwargs.get("alpha", 1) == 1
                bias, a, b = args[0], args[1], args[2]
            else:
                bias, a, b = None, args[0], args[1]
            if a.dtype != torch.float32:
                return func(*args, **kwargs)
            a, b = self._r(a), self._r(b)
            k = a.shape[-1]
            acc = torch.zeros(*a.shape[:-1], b.shape[-1], dtype=torch.float32)
            mm = torch.bmm if a.dim() == 3 else torch.mm
            for s in range(0, k, self.bk):
                acc.add_(mm(a[..., s : s + self.bk].contiguous(), b[..., s : s + self.bk, :].contiguous()))
            self.calls += 1
            return acc + bias if bias is not None else acc
        if func == aten.convolution.default:
            x, w, b, stride, padding, dilation, transposed, output_padding, groups = args[:9]
            if x.dtype != torch.float32:
                return func(*args, **kwargs)
            assert groups == 1
            x, w = self._r(x), self._r(w)
            cin = x.shape[1]
            cb = max(1, cin // 8) if cin > 8 else 1
            acc = None
            for c in range(0, cin, cb):
                wc = w[c : c + cb] if transposed else w[:, c : c + cb]
                part = func(x[:, c : c + cb].contiguous(), wc.contiguous(), None, stride, padding, dilation, transposed, output_padding, groups)
                acc = part if acc is None else acc.add_(part)
            self.calls += 1
            if b is not None:
                acc = acc + b.view(1, -1, *([1] * (acc.dim() - 2)))
            return acc
        if func == aten.sum.dim_IntList:
            x, dims = args[0], list(args[1])
            keep = args[2] if len(args) > 2 else kwargs.get("keepdim", False)
            assert len(dims) == 1 and x.dtype == torch.float32
            d = dims[0] % x.dim()
            n = x.shape[d]
            acc = None
            for s in range(0, n, self.bk):
                part = x.narrow(d, s, min(self.bk, n - s)).sum(d, keepdim=True)
                acc = part if acc is None else acc.add_(part)
            self.calls += 1
            return acc if keep else acc.squeeze(d)
        return func(*args, **kwargs)


_F = torch.float64  # transform matrices are built exactly in fp64, then cast
W23 = {
    "m": 2,
    "BT": torch.tensor([[1, 0, -1, 0], [0, 1, 1, 0], [0, -1, 1, 0], [0, 1, 0, -1]], dtype=_F),
    "G": torch.tensor([[1, 0, 0], [0.5, 0.5, 0.5], [0.5, -0.5, 0.5], [0, 0, 1]], dtype=_F),
    "AT": torch.tensor([[1, 1, 1, 0], [0, 1, -1, -1]], dtype=_F),
}
W43 = {
    "m": 4,
    "BT": torch.tensor(
        [[4, 0, -5, 0, 1, 0], [0, -4, -4, 1, 1, 0], [0, 4, -4, -1, 1, 0], [0, -2, -1, 2, 1, 0], [0, 2, -1, -2, 1, 0], [0, 4, 0, -5, 0, 1]], dtype=_F
    ),
    "G": torch.tensor(
        [[1 / 4, 0, 0], [-1 / 6, -1 / 6, -1 / 6], [-1 / 6, 1 / 6, -1 / 6], [1 / 24, 1 / 12, 1 / 6], [1 / 24, -1 / 12, 1 / 6], [0, 0, 1]], dtype=_F
    ),
    "AT": torch.tensor([[1, 1, 1, 1, 1, 0], [0, 1, -1, 2, -2, 0], [0, 1, 1, 4, 4, 0], [0, 1, -1, 8, -8, 1]], dtype=_F),
}


def winograd(x: torch.Tensor, w: torch.Tensor, b: torch.Tensor | None, P: dict[str, Any], tf32: bool) -> torch.Tensor:
    """F(m x m, 3 x 3) Winograd convolution (stride 1, no padding), in the input's dtype:
    input and filter transforms, a batched GEMM over channels per transformed position
    (operands optionally rounded to TF32 RNE, as a tensor-core Winograd does), output
    transform, bias."""
    dt = x.dtype
    m = P["m"]
    a = m + 2
    BT, G, AT = (P[k].to(dt) for k in ("BT", "G", "AT"))
    n, c, h, wd = x.shape
    k = w.shape[0]
    ho, wo = h - 2, wd - 2
    th, tw = -(-ho // m), -(-wo // m)
    xp = torch.nn.functional.pad(x, (0, tw * m + 2 - wd, 0, th * m + 2 - h))
    d = xp.unfold(2, a, m).unfold(3, a, m)  # n c th tw a a
    V = torch.einsum("ij,nctwjk,lk->nctwil", BT, d, BT)
    U = torch.einsum("ij,kcjl,ml->kcim", G, w, G)
    if tf32:
        V, U = round_tf32(V.contiguous(), "rne"), round_tf32(U.contiguous(), "rne")
    Vr = V.permute(4, 5, 0, 2, 3, 1).reshape(a * a, n * th * tw, c)
    Ur = U.permute(2, 3, 1, 0).reshape(a * a, c, k)
    M = torch.bmm(Vr, Ur).reshape(a, a, n, th, tw, k).permute(2, 5, 3, 4, 0, 1)  # n k th tw a a
    Y = torch.einsum("ij,nktwjl,ml->nktwim", AT, M, AT)  # n k th tw m m
    Y = Y.permute(0, 1, 2, 4, 3, 5).reshape(n, k, th * m, tw * m)[:, :, :ho, :wo]
    if b is not None:
        Y = Y + b.to(dt).view(1, -1, 1, 1)
    return Y.contiguous()


class WinogradMode(TorchDispatchMode):
    def __init__(self, P: dict[str, Any], tf32: bool) -> None:
        super().__init__()
        self.P, self.tf32 = P, tf32
        self.calls = 0

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        kwargs = kwargs or {}
        if func == aten.convolution.default and args[0].dtype == torch.float32:
            x, w, b, stride, padding, dilation, transposed, _, groups = args[:9]
            assert tuple(stride) == (1, 1) and tuple(padding) == (0, 0) and tuple(dilation) == (1, 1)
            assert not transposed and groups == 1 and tuple(w.shape[-2:]) == (3, 3)
            self.calls += 1
            return winograd(x, w, b, self.P, self.tf32)
        return func(*args, **kwargs)


def winograd_selftest() -> dict[str, float]:
    """Both transforms against a direct fp64 convolution, run in fp64 (exactness check)."""
    g = torch.Generator().manual_seed(0)
    x = torch.randn(2, 5, 13, 11, generator=g, dtype=torch.float64)
    w = torch.randn(7, 5, 3, 3, generator=g, dtype=torch.float64)
    b = torch.randn(7, generator=g, dtype=torch.float64)
    ref = torch.nn.functional.conv2d(x, w, b)
    return {name: float((winograd(x, w, b, P, False) - ref).abs().max()) for name, P in (("wino23", W23), ("wino43", W43))}


# --- statistics --------------------------------------------------------------------------


def errs(x: torch.Tensor, r: torch.Tensor) -> dict[str, Any]:
    d = (x.double() - r).reshape(-1)
    finite = bool(torch.isfinite(d).all())
    d = torch.nan_to_num(d, nan=math.inf)
    dd = d * d
    pad = (-dd.numel()) % BLOCK
    if pad:
        dd = torch.cat([dd, dd.new_zeros(pad)])
    bsq = dd.reshape(-1, BLOCK).sum(dim=1)
    ra = r.reshape(-1).abs()
    e_reg = float((d.abs() / (ra + KAPPA * float(ra.max()))).max())
    return {"linf": float(d.abs().max()), "l2": float(torch.sqrt(dd.sum())), "bsq": bsq, "e_reg": e_reg, "finite": finite}


def score(s: dict[str, Any], ys: list[dict[str, Any]], rinf: float, rblock_rms: float) -> dict[str, float]:
    ninf = max(y["linf"] for y in ys)
    nb = torch.stack([y["bsq"] for y in ys]).max(dim=0).values
    rms2 = float(nb.mean())
    fb2 = (FLOOR_REL * rblock_rms) ** 2
    floor_nf = torch.clamp(nb, min=rms2 if rms2 > 0 else 1e-300)
    floor_f = torch.clamp(nb, min=max(rms2, fb2))
    T = max(MULT * max(y["e_reg"] for y in ys), T_FLOOR)
    return {
        "rho_inf": s["linf"] / max(ninf, FLOOR_REL * rinf),
        "rho_block": float(torch.sqrt(s["bsq"] / floor_f).max()),
        "rho_inf_nofloor": (s["linf"] / ninf) if ninf > 0 else (0.0 if s["linf"] == 0 else math.inf),
        "rho_block_nofloor": float(torch.sqrt(s["bsq"] / floor_nf).max()) if rms2 > 0 else (0.0 if s["linf"] == 0 else math.inf),
        "e_over_T": s["e_reg"] / T,
        "floor_binds_inf": ninf < FLOOR_REL * rinf,
        "floor_binds_block": rms2 < fb2,
    }


def decoys(r: torch.Tensor, seed: int) -> dict[str, Any]:
    flat = r.reshape(-1)
    n = flat.numel()
    rms = float(torch.sqrt((flat * flat).mean()))

    def tile() -> torch.Tensor:
        t = flat.clone()
        t[n - max(1, n // 64) :] = 0
        return t.reshape(r.shape)

    def single() -> torch.Tensor:
        t = flat.clone()
        t[int(flat.abs().argmax())] = 0
        return t.reshape(r.shape)

    def noise() -> torch.Tensor:
        g = torch.Generator().manual_seed(seed + 1)
        return r + 1e-2 * rms * torch.randn(r.shape, generator=g, dtype=r.dtype)

    return {
        "zeros": lambda: torch.zeros_like(r),
        "negation": lambda: -r,
        "tile_missing_1of64": tile,
        "single_max_zeroed": single,
        "gain_1e-2": lambda: r * (1 + 1e-2),
        "noise_1e-2": noise,
        "gain_1e-3": lambda: r * (1 + 1e-3),
    }


# --- one draw ----------------------------------------------------------------------------


def alternatives(problem: str) -> dict[str, Any]:
    alts: dict[str, Any] = {}
    if problem == "L1/47":
        alts["seq1_fp32"] = lambda: KBlockMode(1)
        alts["kblock32_fp32"] = lambda: KBlockMode(32)
        return alts
    alts["kblock_fp32"] = lambda: KBlockMode(32)
    alts["kblock_tf32_rne"] = lambda: KBlockMode(32, "rne")
    alts["kblock_tf32_rz"] = lambda: KBlockMode(32, "rz")
    if problem in WINOGRAD:
        for nm, P in (("wino23", W23), ("wino43", W43)):
            alts[f"{nm}_fp32"] = (lambda P=P: WinogradMode(P, False))
            alts[f"{nm}_tf32"] = (lambda P=P: WinogradMode(P, True))
    if problem in SR_PROBLEMS:
        for s in SR_SEEDS:
            alts[f"tf32_sr_s{s}"] = (lambda s=s: TF32Mode("sr", seed=s))
    return alts


#: which policies hold each alternative to be a correct output (truncation is
#: D14's call: it is reported under the RNE yardstick as well, labelled)
def correct_under(name: str) -> list[str]:
    if name.endswith("_fp32"):
        return ["strict", "tf32_rne", "tf32_ext"]
    if "rz" in name:
        return ["tf32_ext"]
    return ["tf32_rne", "tf32_ext"]


def run_draw(problem: str, ref: torch.nn.Module, inputs: list[Any], seed: int) -> dict[str, Any]:
    t0 = time.time()
    timings: dict[str, float] = {}
    with torch.no_grad():
        dbl = [x.double() if isinstance(x, torch.Tensor) and x.is_floating_point() else x for x in inputs]
        r = first_tensor_outputs(copy.deepcopy(ref).double()(*dbl))[0].detach()
        del dbl
        rinf = float(r.abs().max())
        nblocks = -(-r.numel() // BLOCK)
        rblock_rms = math.sqrt(float((r.double() * r.double()).sum()) / nblocks)

        def fwd(mode_factory: Any | None) -> tuple[torch.Tensor, int]:
            t = time.time()
            m = copy.deepcopy(ref)
            if mode_factory is None:
                out, calls = first_tensor_outputs(m(*inputs))[0].detach(), -1
            else:
                mode = mode_factory()
                with mode:
                    out = first_tensor_outputs(m(*inputs))[0].detach()
                calls = getattr(mode, "calls", -1) if not isinstance(mode, TF32Mode) else sum(mode.calls.values())
            return out, calls, time.time() - t

        ys: dict[str, dict[str, Any]] = {}
        for name, fac in (("fp32", None), ("tf32_rne", lambda: TF32Mode("rne")), ("tf32_rz", lambda: TF32Mode("rz"))):
            x, _, dt = fwd(fac)
            timings[name] = dt
            ys[name] = errs(x, r)
            del x
        out: dict[str, Any] = {"yardstick": {k: {kk: v[kk] for kk in ("linf", "l2", "e_reg")} for k, v in ys.items()}, "alternatives": {}, "decoys": {}}

        def all_scores(s: dict[str, Any]) -> dict[str, Any]:
            return {pol: score(s, [ys[m] for m in members], rinf, rblock_rms) for pol, members in YARDSTICKS.items()}

        for name, fac in alternatives(problem).items():
            x, calls, dt = fwd(fac)
            timings[name] = dt
            if calls == 0:
                raise RuntimeError(f"{name}: the alternative algorithm intercepted no op")
            s = errs(x, r)
            out["alternatives"][name] = {
                "calls": calls,
                "linf": s["linf"],
                "l2": s["l2"],
                "finite": s["finite"],
                "bitwise_equal_to": [m for m, y in ys.items() if y["linf"] == s["linf"] and y["l2"] == s["l2"]],
                "correct_under": correct_under(name),
                "scores": all_scores(s),
            }
            del x
        for name, make in decoys(r, seed).items():
            s = errs(make(), r)
            out["decoys"][name] = {"linf": s["linf"], "l2": s["l2"], "scores": all_scores(s)}
        out["oracle"] = {"r_inf": rinf, "r_block_rms": rblock_rms, "numel": r.numel()}
    timings["total"] = time.time() - t0
    out["timings"] = timings
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("problem")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--out", default=str(HERE / "alt"))
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    torch.backends.nnpack.set_flags(False)
    short = a.problem
    if short not in PLAN:
        raise SystemExit(f"{short} is not one of the study's S1-cal problems")
    pid = cs.full_problem_id(short)
    guard = cs.assert_non_evaluation(pid)
    selftest = winograd_selftest()
    if max(selftest.values()) > 1e-9:
        raise SystemExit(f"winograd self-test failed: {selftest}")
    src = cs.problem_lib.load_problem_source(pid)
    manifest = json.loads((cs.REPO / "harness/q1/data/shape_manifest.json").read_text())["problems"]
    ref, get_inputs = audit_run._reference_module(src, cs.REPLICATE, cs.CPU)
    picks, subset = PLAN[short]
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for channel, idxs in picks.items():
        plan = audit_run._draw_plan(channel, pid, src, cs.REPLICATE, get_inputs, manifest.get(pid))
        for index in idxs:
            if index >= len(plan):
                continue
            draw = plan[index]
            cfg = draw["config_id"]
            path = out_dir / f"{short.replace('/', '-')}__{cfg.replace('/', '_')}.json"
            if path.exists():
                print("exists", path.name, flush=True)
                continue
            inputs = process_inputs(draw["raw"](), cs.CPU, "preserve")
            full = int(inputs[0].shape[0])
            if subset and full > subset:
                if short not in SLICEABLE:
                    raise SystemExit(f"{short} couples the batch; no subset")
                inputs = [inputs[0][:subset].contiguous(), *inputs[1:]]
            print("run", short, cfg, flush=True)
            res = run_draw(short, ref, inputs, int(draw["facts"]["seed"]))
            rec = {
                "schema": "q1-audit-metric-study/alt-draw/1",
                "problem_id": pid,
                "problem": short,
                "channel": channel,
                "config_id": cfg,
                "batch": {"full": full, "evaluated": int(inputs[0].shape[0])},
                "guard": guard,
                "winograd_selftest_fp64_max_abs": selftest,
                "env": {"torch": torch.__version__, "platform": platform.platform(), "threads": torch.get_num_threads()},
                "code_sha256": {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in ("alt_algorithms.py", "cpu_study.py", "tf32emu.py")},
                **res,
            }
            path.write_text(json.dumps(rec, indent=1, sort_keys=True))
            print("done", short, cfg, "%.1fs" % res["timings"]["total"], flush=True)


if __name__ == "__main__":
    main()
