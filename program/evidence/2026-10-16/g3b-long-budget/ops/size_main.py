"""G3b sizing (EXPLORATORY; run on the Mac from the pilot's text-free records and G3's committed
per-request data). Not part of the analysis.

1. From each pilot worker (``<dir>/records.json``, ``phase-stats.npz``): the decode step time
   against the total context held by the running sequences, at 23 running. A request's context
   at time t is its prompt plus the tokens it had generated, interpolated linearly between its
   first token and its end (or the phase end). Fit: ms per step = a + c * context (Mtok).
2. A no-preemption FCFS simulation of the main run (153 requests in G3's order, 23 slots) with
   G3's lengths on these questions; a rollout that hit G3's 32,768-token cap continues with an
   exponential tail whose 4K-token hazard is G3's share of rollouts still running at 28K that
   ended by 32K (fp32 0.29, bf16 0.21; independent check), times a scale (1.0 and 0.6), capped at
   81,920. Step time per token = a + b * running + c * context, with b from G3's sizing
   (0.036 ms fp32, 0.018 ms bf16 per running sequence) and the pilot's a and c.
Usage: python size_main.py <g3 per-request.jsonl.gz> <pilot worker dir> [<pilot worker dir>...]
"""

import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

G3_B = {"fp32": 0.036, "bf16": 0.018}
HAZARD_4K = {"fp32": 0.29, "bf16": 0.21}


def fit_pilot(worker: Path) -> dict:
    rec = json.loads((worker / "records.json").read_text())
    st = np.load(worker / "phase-stats.npz")
    t, tok = st["t"], st["tokens"]
    end = float(t[-1])
    reqs = []
    for r in rec["requests"]:
        if r["first_token_s"] is None:
            continue
        t1 = r["finished_s"] if r["finished_s"] is not None else end
        reqs.append((r["first_token_s"], t1, r["prompt_len"], r["completion_len"]))
    S = np.zeros_like(t)
    B = np.zeros_like(t)
    for t0, t1, p, n in reqs:
        on = (t >= t0) & (t <= t1)
        frac = np.clip((t - t0) / max(t1 - t0, 1e-9), 0, 1)
        S += on * (p + frac * n)
        B += on
    dt = np.diff(t) * 1000.0
    S_mid, B_mid, n_mid = S[1:], B[1:], tok[1:]
    keep = (n_mid >= 20) & (B_mid >= 20) & (dt < 200)  # decode steps at about 23 running
    A = np.column_stack([np.ones(keep.sum()), S_mid[keep] / 1e6])
    coef, *_ = np.linalg.lstsq(A, dt[keep], rcond=None)
    return {
        "arm": rec["arm"],
        "steps_used": int(keep.sum()),
        "a_ms": float(coef[0]),
        "c_ms_per_mtok": float(coef[1]),
        "context_mtok_range": [float(S_mid[keep].min() / 1e6), float(S_mid[keep].max() / 1e6)],
        "tok_per_s": float(tok.sum() / end),
        "requests_finished": sum(1 for r in rec["requests"] if r["finish_reason"] == "stop"),
    }


def sim(lens, slots, a, b, c, chunk=256):
    lens = np.array(lens, dtype=float)
    n = len(lens)
    gen = np.zeros(n)
    nxt, t, active = 0, 0.0, []
    while True:
        while nxt < n and len(active) < slots:
            active.append(nxt)
            nxt += 1
        if not active:
            return t
        act = np.array(active)
        S = (gen[act] + 600).sum()
        step = min(chunk, (lens[act] - gen[act]).min())
        t += (a + b * len(act) + c * S / 1e6) / 1000 * step
        gen[act] += step
        active = [i for i in active if gen[i] < lens[i]]


def main() -> None:
    with gzip.open(sys.argv[1], "rt") as handle:
        rows = [json.loads(x) for x in handle]
    fits = [fit_pilot(Path(p)) for p in sys.argv[2:]]
    for f in fits:
        print(json.dumps(f))
    m = [
        r
        for r in rows
        if r["phase"] == "main" and r["model"] == "qwen3.5-4b" and r["task"] == "math"
    ]
    qs = sorted({r["question_index"] for r in m if r["finish_reason"] == "length"})
    by = {(r["arm"], r["seed"], r["question_index"]): r for r in m}
    rng = np.random.default_rng(0)
    for f in fits:
        arm = f["arm"]
        for scale in (1.0, 0.6):
            walls, toks = [], []
            lam = -math.log(1 - HAZARD_4K[arm] * scale) / 4096
            for _ in range(30):
                lens = []
                for s in (42, 43, 44):
                    for q in qs:
                        r = by[(arm, s, q)]
                        L = r["completion_len"]
                        if r["finish_reason"] == "length":
                            L = min(81920, 32768 + int(rng.exponential(1 / lam)))
                        lens.append(L)
                walls.append(sim(lens, 23, f["a_ms"], G3_B[arm], f["c_ms_per_mtok"]))
                toks.append(sum(lens))
            print(f"{arm} hazard x{scale}: wall mean {np.mean(walls):.0f} s, p90 "
                  f"{np.percentile(walls, 90):.0f} s, max {np.max(walls):.0f} s, tokens "
                  f"{np.mean(toks) / 1e6:.2f}M")


if __name__ == "__main__":
    main()
