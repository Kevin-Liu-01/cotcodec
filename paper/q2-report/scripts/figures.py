"""Draw the Q2 report's Figures 2 and 3 from committed files (CPU, no network).

    PYTHONPATH=. python paper/q2-report/scripts/figures.py

Figure 2 reads S1a's registered report (`report-guarded.json`): delta pooled and per size and
the per-size session shift, with their 95% task-cluster bootstrap intervals, and pooled delta's
90% t interval, for the 32-task primary set and the 113-task registered secondary set.
Figure 3 reads `paper/q2-report/data/variance-shares.json` (written by `variance_shares.py`):
the design study's model-based probability-scale variance shares. Both write SVG with a fixed
hash salt so reruns are byte-stable.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["svg.hashsalt"] = "q2-report"
plt.rcParams["font.size"] = 9

REPORT = Path("program/evidence/2026-10-10/q2-stage1-analysis/report/report-guarded.json")
SHARES = Path("paper/q2-report/data/variance-shares.json")
OUT = Path("paper/q2-report/figures")


def figure2() -> None:
    report = json.loads(REPORT.read_text())
    sets = [
        ("primary", "32 tasks (primary)"),
        ("secondary_base_plus_completed_extension", "113 tasks (secondary)"),
    ]
    rows = [
        ("delta", "δ pooled"),
        ("delta_4B", "δ 4B"),
        ("delta_9B", "δ 9B"),
        ("session_shift_4B", "session shift 4B"),
        ("session_shift_9B", "session shift 9B"),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    colors = {"primary": "#1f4e79", "secondary_base_plus_completed_extension": "#9c6500"}
    for j, (key, label) in enumerate(sets):
        est = report[key]["estimates"]
        t90 = report[key]["tests"]["delta_paired_t"]["ci90_t"]
        for i, (name, _) in enumerate(rows):
            y = len(rows) - 1 - i + (0.15 if j == 0 else -0.15)
            e = est[name]
            lo, hi = (100 * v for v in e["ci95"])
            ax.plot([lo, hi], [y, y], color=colors[key], lw=1.4)
            ax.plot(
                100 * e["estimate"],
                y,
                "o",
                color=colors[key],
                ms=4,
                label=label if i == 0 else None,
            )
            if name == "delta":
                ax.plot(
                    [100 * t90[0], 100 * t90[1]],
                    [y, y],
                    color=colors[key],
                    lw=4,
                    alpha=0.35,
                    solid_capstyle="butt",
                )
    ax.axvline(0, color="#444", lw=0.8)
    for x in (-7.5, 7.5):
        ax.axvline(x, color="#888", lw=0.8, ls="--")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[1] for r in rows][::-1])
    ax.set_xlabel("percentage points (H-GA − H-OSW-fixed; session 2 − session 1)")
    ax.set_title(
        "S1a: harness difference and session shift (95% bootstrap; thick: δ's 90% t)", fontsize=9
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig2-harness-and-session.svg", metadata={"Date": None})
    plt.close(fig)


def figure3() -> None:
    shares = json.loads(SHARES.read_text())["shares"]
    order = ["N0", "P0", "PR", "P4", "P4sf"]
    groups = [
        ("task", ["task"], "#1f4e79"),
        ("rerun", ["rerun"], "#9c6500"),
        ("task x harness", ["task_x_harness"], "#2e7d32"),
        (
            "session terms",
            ["session", "task_x_session", "harness_x_session", "task_x_harness_x_session"],
            "#7b1fa2",
        ),
        ("harness", ["harness"], "#c62828"),
    ]
    labels, bars = [], []
    for cal in order:
        for size in ("4B", "9B"):
            labels.append(f"{cal} {size}" + (" (fails check)" if cal == "N0" else ""))
            bars.append([sum(shares[cal][size][k] for k in keys) for _, keys, _ in groups])
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for i, values in enumerate(bars):
        y = len(bars) - 1 - i
        left = 0.0
        for (name, _, color), v in zip(groups, values, strict=True):
            ax.barh(y, v, left=left, color=color, height=0.7, label=name if i == 0 else None)
            left += v
    ax.set_yticks(range(len(bars)))
    ax.set_yticklabels(labels[::-1], fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of outcome variance (probability scale)")
    ax.set_title(
        "Model-based variance split by calibration (N0 fails the extended check)", fontsize=9
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=5, frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig3-variance-shares.svg", metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    figure2()
    figure3()


if __name__ == "__main__":
    main()
