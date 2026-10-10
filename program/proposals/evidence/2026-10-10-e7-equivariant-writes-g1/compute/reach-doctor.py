#!/usr/bin/env python3
"""S3: state-free reach of the A0 layer graph, checked by perturbation (NumPy, float64, CPU).

Builds a small random NumPy model with the A0 layer order of the measured
134M configuration (12 layers; layers 3, 7 and 11, zero-indexed, are causal
sliding-window attention with window W = 512, meaning position i attends to
positions i-511 .. i; the other nine are Gated DeltaNet layers with a causal
depthwise short convolution of kernel 4 on q, k and v, the gated delta-rule
recurrence, and an output gate; pre-norm RMSNorm and a SiLU MLP after every
mixer). It measures the derivative of the output at p_a with respect to the
input at position p = p_a - delta by the complex-step method (input
x + i h e_p with h = 1e-30, derivative Im(f) / h). The complex step has no
subtractive cancellation, so a derivative of 1e-20 is still resolved, and an
imaginary part is exactly zero only where no computational path exists. A
finite difference cannot make that distinction beyond about 1e-16 relative.
Two modes are compared:

  full        the recurrent state is carried as in the model;
  state_free  the previous state is zeroed at every step, so a GDN layer sees
              only its own token after the short convolution.

The registered claim it checks: with the state removed, information can move
at most 3 x 511 + 9 x 3 = 1,560 positions, so recall of a fact whose last token
is at least 1,600 positions before the answer position needs the recurrent
state. It checks the arithmetic and the window and convolution semantics of
the layer graph. It is not the fla kernel, not the trained model and not a
pilot.

It also reports, by Monte Carlo, the share of GDN heads whose initial decay
timescale exceeds 512, 1,560 and 1,600 tokens under the fla 0.5.2
initialization (A ~ U(0, 16), dt log-uniform on [0.001, 0.1]; per-token decay
exp(-A * softplus(a_proj x + dt_bias)), timescale 1 / (A * softplus(.))), with
the input term a_proj x set to zero or drawn N(0, 0.5^2) (an assumption).

Seeds 42, 43, 44. Usage: reach-doctor.py <output.json>
"""

from __future__ import annotations

import json
import sys

import numpy as np

W = 512
CONV = 4
LAYERS = 12
D = 8
HEADS = 2
HD = D // HEADS


H = 1e-30


def rmsnorm(x):
    return x / np.sqrt((x * x).mean(-1, keepdims=True) + 1e-6)


def unit(x):
    return x / (np.sqrt((x * x).sum(1, keepdims=True)) + 1e-6)


def silu(x):
    return x / (1.0 + np.exp(-x))


def causal_conv(x, w):
    # x: (L, C); w: (CONV, C); out[t] = sum_j w[j] * x[t - j]
    out = np.zeros_like(x)
    for j in range(CONV):
        out[j:] += w[j] * x[: len(x) - j]
    return out


class Model:
    def __init__(self, rng):
        self.layers = []
        for i in range(LAYERS):
            p = {"swa": i % 4 == 3}
            s = 0.5 / np.sqrt(D)
            for name in ("q", "k", "v", "o", "g"):
                p[name] = rng.normal(0, s, (D, D))
            p["a"] = rng.normal(0, s, (D, HEADS))
            p["b"] = rng.normal(0, s, (D, HEADS))
            p["A"] = rng.uniform(0.05, 0.5, HEADS)
            p["conv"] = {n: rng.normal(0, 0.5, (CONV, D)) for n in ("q", "k", "v")}
            p["m1"] = rng.normal(0, s, (D, 4 * D))
            p["m2"] = rng.normal(0, 0.5 / np.sqrt(4 * D), (4 * D, D))
            self.layers.append(p)

    def swa(self, p, h):
        L = len(h)
        q, k, v = h @ p["q"], h @ p["k"], h @ p["v"]
        out = np.zeros_like(h)
        idx = np.arange(L)
        mask = (idx[None, :] <= idx[:, None]) & (idx[None, :] >= idx[:, None] - (W - 1))
        for hh in range(HEADS):
            sl = slice(hh * HD, (hh + 1) * HD)
            sc = (q[:, sl] @ k[:, sl].T) / np.sqrt(HD)
            sc = np.where(mask, sc, -np.inf)
            sc = np.exp(sc - sc.real.max(1, keepdims=True))
            sc = sc / sc.sum(1, keepdims=True)
            out[:, sl] = sc @ v[:, sl]
        return out @ p["o"]

    def gdn(self, p, h, state_free):
        L = len(h)
        q = silu(causal_conv(h @ p["q"], p["conv"]["q"]))
        k = silu(causal_conv(h @ p["k"], p["conv"]["k"]))
        v = silu(causal_conv(h @ p["v"], p["conv"]["v"]))
        alpha = np.exp(-p["A"] * np.log1p(np.exp(h @ p["a"])))  # (L, HEADS)
        beta = 1.0 / (1.0 + np.exp(-(h @ p["b"])))
        out = np.zeros_like(h)
        for hh in range(HEADS):
            sl = slice(hh * HD, (hh + 1) * HD)
            kk = unit(k[:, sl])
            qq = unit(q[:, sl])
            S = np.zeros((HD, HD), dtype=complex)
            for t in range(L):
                prev = np.zeros((HD, HD), dtype=complex) if state_free else S
                S = alpha[t, hh] * prev @ (np.eye(HD) - beta[t, hh] * np.outer(kk[t], kk[t])) \
                    + beta[t, hh] * np.outer(v[t, sl], kk[t])
                out[t, sl] = S @ qq[t]
        gate = silu(h @ p["g"])
        return (out * gate) @ p["o"]

    def forward(self, x, state_free):
        for p in self.layers:
            h = rmsnorm(x)
            x = x + (self.swa(p, h) if p["swa"] else self.gdn(p, h, state_free))
            x = x + silu(rmsnorm(x) @ p["m1"]) @ p["m2"]
        return x


def reach(seed: int, length: int, deltas: list[int]) -> dict:
    rng = np.random.default_rng(seed)
    model = Model(rng)
    x = rng.normal(0, 1, (length, D)).astype(complex)
    pa = length - 1
    rows = []
    for d in deltas:
        xp = x.copy()
        xp[pa - d] += 1j * H
        row = {"delta": d}
        for mode in ("full", "state_free"):
            row[mode] = float(np.abs(model.forward(xp, mode == "state_free")[pa].imag).max() / H)
        rows.append(row)
    return {"seed": seed, "length": length, "rows": rows}


def init_timescales(seed: int, n: int, input_sd: float) -> dict:
    rng = np.random.default_rng(seed)
    A = rng.uniform(0, 16, n)
    dt = np.exp(rng.uniform(np.log(1e-3), np.log(1e-1), n))
    dt = np.maximum(dt, 1e-4)
    dt_bias = dt + np.log(-np.expm1(-dt))
    sp = np.log1p(np.exp(dt_bias + rng.normal(0, input_sd, n))) if input_sd > 0 else dt
    tau = 1.0 / np.maximum(A * sp, 1e-12)
    return {f"share_tau_gt_{t}": round(float((tau > t).mean()), 4) for t in (512, 1560, 1600)}


def main() -> int:
    out_path = sys.argv[1]
    bound = 3 * (W - 1) + 9 * (CONV - 1)
    deltas = [1, 100, 511, 512, 1022, 1023, 1533, 1534, 1557, 1559, 1560, 1561, 1562, 1580, 1600, 1700]
    runs = [reach(s, 1760, deltas) for s in (42, 43, 44)]
    checks = []
    for run in runs:
        for row in run["rows"]:
            expect_free = row["delta"] <= bound
            checks.append({
                "seed": run["seed"], "delta": row["delta"],
                "state_free_changes": row["state_free"] > 0.0,
                "state_free_expected": expect_free,
                "full_changes": row["full"] > 0.0,
                "ok": (row["state_free"] > 0.0) == expect_free and row["full"] > 0.0,
            })
    timescales = {f"input_sd={sd}": {str(s): init_timescales(s, 200_000, sd) for s in (42, 43, 44)} for sd in (0.0, 0.5)}
    res = {
        "script": "reach-doctor.py",
        "claimed_state_free_bound": bound,
        "bound_formula": "3 SWA layers x (W - 1) + 9 GDN layers x (conv kernel - 1) = 3 x 511 + 9 x 3",
        "gate_bin_min_distance": 1600,
        "all_checks_ok": all(c["ok"] for c in checks),
        "runs": runs,
        "checks": checks,
        "init_decay_timescales_fla_0_5_2": timescales,
        "scope": "NumPy stand-in of the A0 layer graph (D = 8, 2 heads, float64); checks reach arithmetic and window/convolution semantics only; not the fla kernels, not a trained model, not a pilot.",
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print("REACH_DOCTOR", "PASS" if res["all_checks_ok"] else "FAIL", "bound", bound)
    return 0 if res["all_checks_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
