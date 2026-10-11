"""Per-request prices from S1a's realized step costs and the per-job caps (registration v2,
section 11).

Cap rule (the Q2 design study's realized-cost rule, adopted explicitly):

    cap (min) = ceil(3 min USR1 lead + 2 min x engine starts + W x 1.2 (DR4) x 1.05 (re-queue))

with W the job's work at the HIGH price:

* **batch-1 work** (E-det, E-c1 cold, P0): per request, S1a's realized step-k latency (4B
  H-OSW-fixed, measured at about 3.7 requests in flight with the system prompt cached) plus a
  full uncached prefill of the step's prompt, plus 0.05 s for the encoder-cache reset. Central:
  the mean latency and the prefill at 14,519 tok/s (S1a's step-1 median time to first token over
  about 2,400 uncached tokens); high: the 95th-percentile latency and the prefill at half that
  rate. The prefill double-counts what S1a already paid for the image, so the high price is
  conservative;
* **warm cache hits** (E-c1 warm): S1a's 95th-percentile step latency (high), its mean (central);
* **loaded passes** (E-s1a, E-nc): simulated, not averaged. A pass ends when the slowest of its
  ``streams`` lanes has replied: per lane, a uniform start offset on [0, think) plus, per item,
  a latency resampled from S1a's realized step-k latencies (times 1.25 for high) and an
  exponential think time after every item but the last, with the mean think time set so that
  3.7 requests are in flight on average (S1a's bridge samples). W is the 95th percentile of the
  job's simulated total over 20,000 draws (numpy PCG64, seed 42), plus 0.2 s of resets per pass.
  Wave 1 priced a pass as one lane's mean and under-capped J3 (overrun probability 0.52-0.96).

The 8 GPU-h line of D20/D22 is read on the sum of the caps, conditional jobs included. P0
measures the batch-1 and loaded prices before any J job is submitted (``p0.timing_gate``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

LEAD_MIN = 3.0
ENGINE_START_MIN = 2.0  # S1a's engine start: 95-98 s (bridge samples)
F_DR4, F_REQ = 1.2, 1.05
RESET_S = 0.05
PASS_RESET_S = 0.2
PREFILL_CENTRAL_TOK_S = 14519.0  # 2,400 uncached tokens / S1a's step-1 median ttft 0.1653 s
HIGH_LATENCY_SCALE = 1.25
SIM_DRAWS = 20000
SIM_SEED = 42


@dataclass(frozen=True)
class StepCost:
    """S1a's realized costs of one step (4B H-OSW-fixed)."""

    step: int
    prompt_tokens_mean: float
    latency_mean_s: float
    latency_p95_s: float
    latencies_s: tuple[float, ...] = field(repr=False, default=())

    def batch1(self, high: bool) -> float:
        rate = PREFILL_CENTRAL_TOK_S / (2.0 if high else 1.0)
        base = self.latency_p95_s if high else self.latency_mean_s
        return base + self.prompt_tokens_mean / rate + RESET_S

    def warm(self, high: bool) -> float:
        return self.latency_p95_s if high else self.latency_mean_s


def step_costs(
    digest_rows: Sequence[Mapping[str, Any]], steps: Sequence[int] = (1, 2)
) -> dict[int, StepCost]:
    """From the A0 digest table (4B H-OSW-fixed episodes)."""
    out = {}
    eps = [r for r in digest_rows if r["size"] == "4B" and r["harness"] == "H-OSW-fixed"]
    for k in steps:
        rows = [r["steps"][k - 1] for r in eps if len(r["steps"]) >= k]
        lat = np.array([s["lat"] for s in rows], dtype=float)
        ptok = np.array([s["ptok"] for s in rows], dtype=float)
        out[k] = StepCost(
            step=k,
            prompt_tokens_mean=float(ptok.mean()),
            latency_mean_s=float(lat.mean()),
            latency_p95_s=float(np.quantile(lat, 0.95, method="lower")),
            latencies_s=tuple(float(x) for x in lat),
        )
    return out


def cap_minutes(work_high_s: float, engine_starts: int = 1) -> int:
    return math.ceil(
        LEAD_MIN + ENGINE_START_MIN * engine_starts + (work_high_s / 60.0) * F_DR4 * F_REQ
    )


def think_mean(
    costs: Mapping[int, StepCost],
    counts: Mapping[int, int],
    streams: int = 20,
    target_inflight: float = 3.7,
) -> float:
    n = sum(counts.values())
    mean_lat = sum(costs[k].latency_mean_s * c for k, c in counts.items()) / n
    return mean_lat * (streams / target_inflight - 1.0)


def simulate_loaded(
    costs: Mapping[int, StepCost],
    counts: Mapping[int, int],
    passes: int,
    *,
    streams: int = 20,
    think_s: float | None = None,
    scale: float = 1.0,
    draws: int | None = None,
    seed: int = SIM_SEED,
    latency_pool: Mapping[int, Sequence[float]] | None = None,
) -> np.ndarray:
    """Simulated wall time (s) of ``passes`` loaded passes of ``counts`` items per step: per
    pass, a seeded shuffle deals items to lanes round-robin (``replay.loaded_schedule``'s rule),
    each item's latency is resampled from S1a's realized latencies of its step, each lane waits a
    uniform start offset and an exponential think time after every item but its last, and the
    pass ends when the slowest lane has replied."""
    draws = SIM_DRAWS if draws is None else draws
    rng = np.random.default_rng(seed)
    think = think_s if think_s is not None else think_mean(costs, counts, streams)
    step_arr = np.asarray([k for k, c in sorted(counts.items()) for _ in range(c)])
    n = len(step_arr)
    per_lane = math.ceil(n / streams)
    pad = per_lane * streams - n
    pools = {
        k: np.asarray(latency_pool[k] if latency_pool else costs[k].latencies_s, dtype=float)
        for k in counts
    }
    total = np.zeros(draws)
    for _ in range(passes):
        dealt = step_arr[np.argsort(rng.random((draws, n)), axis=1)]
        lat = np.zeros((draws, n))
        for k, pool in pools.items():
            lat = np.where(
                dealt == k, pool[rng.integers(0, len(pool), size=(draws, n))] * scale, lat
            )
        valid = np.ones((draws, n), dtype=bool)
        if pad:
            lat = np.concatenate([lat, np.zeros((draws, pad))], axis=1)
            valid = np.concatenate([valid, np.zeros((draws, pad), dtype=bool)], axis=1)
        # item j -> lane j % streams, position j // streams
        lat = lat.reshape(draws, per_lane, streams)
        valid = valid.reshape(draws, per_lane, streams)
        thinks = rng.exponential(think, size=lat.shape) if think > 0 else np.zeros_like(lat)
        last = valid.sum(axis=1, keepdims=True) - 1
        pos = np.arange(per_lane)[None, :, None]
        thinks = np.where(valid & (pos < last), thinks, 0.0)
        offsets = (
            rng.uniform(0.0, think, size=(draws, streams))
            if think > 0
            else np.zeros((draws, streams))
        )
        lane_time = offsets + (lat + thinks).sum(axis=1)
        total += lane_time.max(axis=1) + PASS_RESET_S
    return total


@dataclass
class Job:
    name: str
    config: str
    arms: str
    conditional: bool = False
    engine_starts: int = 1
    batch1: dict[int, int] = field(default_factory=dict)  # step -> requests at the batch-1 price
    warm: dict[int, int] = field(default_factory=dict)  # step -> warm hits
    loaded_counts: dict[int, int] = field(default_factory=dict)  # step -> items per loaded pass
    loaded_passes: int = 0

    def work(self, costs: Mapping[int, StepCost], high: bool) -> dict[str, float]:
        b1 = sum(costs[k].batch1(high) * n for k, n in self.batch1.items())
        wm = sum(costs[k].warm(high) * n for k, n in self.warm.items())
        loaded = 0.0
        loaded_note = None
        if self.loaded_passes:
            sim = simulate_loaded(
                costs,
                self.loaded_counts,
                self.loaded_passes,
                scale=HIGH_LATENCY_SCALE if high else 1.0,
            )
            loaded = float(np.quantile(sim, 0.95)) if high else float(sim.mean())
            loaded_note = {
                "mean_s": round(float(sim.mean()), 1),
                "p95_s": round(float(np.quantile(sim, 0.95)), 1),
                "p99_s": round(float(np.quantile(sim, 0.99)), 1),
            }
        return {
            "batch1_s": b1,
            "warm_s": wm,
            "loaded_s": loaded,
            "total_s": b1 + wm + loaded,
            "loaded_sim": loaded_note,
        }

    def row(self, costs: Mapping[int, StepCost]) -> dict[str, Any]:
        wc, wh = self.work(costs, False), self.work(costs, True)
        cap = cap_minutes(wh["total_s"], self.engine_starts)
        return {
            "job": self.name,
            "config": self.config,
            "arms": self.arms,
            "conditional": self.conditional,
            "engine_starts": self.engine_starts,
            "requests": {
                "batch1": self.batch1,
                "warm": self.warm,
                "loaded": {"per_pass": self.loaded_counts, "passes": self.loaded_passes},
            },
            "work_min_central": round(wc["total_s"] / 60, 2),
            "work_min_high": round(wh["total_s"] / 60, 2),
            "loaded_sim_central": wc["loaded_sim"],
            "loaded_sim_high": wh["loaded_sim"],
            "cap_min": cap,
            "cap_gpu_h": round(cap / 60, 3),
            "physical_gpu_h_central": round(
                (wc["total_s"] / 60 + ENGINE_START_MIN * self.engine_starts) / 60, 3
            ),
            "arithmetic": (
                f"ceil({LEAD_MIN} + {ENGINE_START_MIN} x {self.engine_starts} + "
                f"{wh['total_s'] / 60:.2f} x {F_DR4} x {F_REQ}) = {cap}"
            ),
        }
