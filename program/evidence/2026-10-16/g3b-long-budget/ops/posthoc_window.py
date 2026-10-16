"""G3b post hoc (EXPLORATORY; text-free, on the Mac): the main bf16 engine's decode rate around the
host-load window of 04:05-04:08 UTC (ops/timing-windows.json), from its phase-stats.npz (per-step
time and tokens) and phase-stats.metrics.jsonl (running sequences), in 60-s bins. Also estimates
the generation time lost in the window: tokens the engine would have produced at the mean rate of
the 5 minutes before it, minus those it produced.
Usage (from the evidence directory): python ops/posthoc_window.py > analysis/posthoc-window.json"""

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
W = HERE / "jobs/1576-main/g3b/qwen3.5-4b-bf16-math"


def utc(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


def main() -> None:
    window = json.loads((HERE / "ops/timing-windows.json").read_text())[0]
    start = next(
        utc(e["utc"])
        for e in map(json.loads, (W / "worker-progress.jsonl").read_text().splitlines())
        if e["event"] == "phase-start"
    )
    st = np.load(W / "phase-stats.npz")
    t, tok = st["t"], st["tokens"]
    samples = [json.loads(x) for x in (W / "phase-stats.metrics.jsonl").read_text().splitlines()]
    ws, we = utc(window["start_utc"]) - start, utc(window["end_utc"]) - start
    bins = []
    for lo in np.arange(ws - 600, we + 420, 60.0):
        hi = lo + 60.0
        m = (t >= lo) & (t < hi)
        run = [s["running"] for s in samples if lo <= s["t"] < hi and "running" in s]
        bins.append(
            {
                "phase_s": [float(lo), float(hi)],
                "tokens": int(tok[m].sum()),
                "tok_per_s": float(tok[m].sum() / 60.0),
                "steps": int(m.sum()),
                "mean_running": float(np.mean(run)) if run else None,
                "in_window": bool(lo < we and ws < hi),
            }
        )
    before = (t >= ws - 300) & (t < ws)
    during = (t >= ws) & (t < we)
    rate_before = tok[before].sum() / 300.0
    produced = tok[during].sum()
    lost_s = (rate_before * (we - ws) - produced) / rate_before if rate_before else None
    out = {
        "window": window,
        "phase_start_utc": datetime.fromtimestamp(start, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_phase_s": [ws, we],
        "rate_before_tok_per_s": float(rate_before),
        "rate_during_tok_per_s": float(produced / (we - ws)),
        "generation_seconds_lost_estimate": float(lost_s) if lost_s is not None else None,
        "phase_wall_s": float(t[-1]),
        "bins_60s": bins,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
