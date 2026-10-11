"""Draw the checker-mutation note's figures from committed evidence (CPU, no network).

    uv run --locked python paper/checker-mutation-note/scripts/figures.py

Run from the repository root. Reads only committed files:

- the adjudicated parent analysis (D81 run 2, D82): per-operator candidate and confirmed shares;
- the confirm campaign's released `outcomes.jsonl`: the z-order operator's statuses and verdicts;
- the confirm results summary: the model raters' decisions on the z-order candidates;
- the K2 job 1186 report summary: in-VM reproduction of the candidate events;
- the G0 `zinv` validation (v3): the corrected comparator on the stored candidates.

Writes `figures/fig1-operator-shares.svg`, `figures/fig2-zorder-stages.svg` and
`data/derived.json` (counts the note quotes that no committed file states directly). SVG output
uses a fixed hash salt, so reruns are byte-stable.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["svg.hashsalt"] = "checker-mutation-note"
plt.rcParams["font.size"] = 9

EV = Path("program/evidence")
ADJ = EV / "2026-10-11/q2-mutation-adjudication-v2/analysis/analysis.json"
OUTCOMES = EV / "2026-10-08/q2-mutation-confirm/results/released/confirm-mutants-v1/outcomes.jsonl"
CONFIRM_SUMMARY = EV / "2026-10-08/q2-mutation-confirm/results/summary.json"
K2 = EV / "2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/report/k2-summary.json"
ZINV = EV / "2026-10-08/q2-stage1-g0/zinv/zinv-validation-v3.json"
NOTE = Path("paper/checker-mutation-note")
ZORDER = "pptx.eq.zorder_nonoverlap"

INK = "#222222"
CAND = "#1f4e79"
CONF = "#b5651d"
GREY = "#9a9a9a"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def outcomes() -> list[dict]:
    return [json.loads(line) for line in OUTCOMES.read_text().splitlines() if line.strip()]


def derived() -> dict:
    """Counts from `outcomes.jsonl` and the zinv rows that the note quotes."""
    rows = outcomes()
    z_all = [r for r in rows if r["operator"] == ZORDER]
    in_pop = [
        r
        for r in z_all
        if r["lock_status"] == "evaluable" and not r["probe_touched"] and not r["probe_informed"]
    ]
    by_family_verdict: dict[str, dict[str, int]] = {}
    for r in in_pop:
        fam = by_family_verdict.setdefault(r["checker_family"], {})
        fam[r["lock_verdict"]] = fam.get(r["lock_verdict"], 0) + 1
    population = [
        r
        for r in rows
        if r["lock_status"] == "evaluable" and not r["probe_touched"] and not r["probe_informed"]
    ]
    zinv = load(ZINV)
    zrows = [r for r in zinv["rows"] if r["operator"] == ZORDER]
    zinv_readings = Counter(f"{r['reading']}|raw={r['raw']}|zinv={r['zinv']}" for r in zrows)
    should_fail = [r for r in zinv["rows"] if (r["label"] or "").startswith("should_fail")]
    zinv_should_fail = Counter(f"raw={r['raw']}|zinv={r['zinv']}" for r in should_fail)
    return {
        "schema": "checker-mutation-note-derived-v1",
        "inputs": {
            "outcomes": str(OUTCOMES),
            "zinv": str(ZINV),
        },
        "population_outside_probe_cells": {
            "mutants": len(population),
            "tasks": len({r["task_id"] for r in population}),
        },
        "zorder_planned": len(z_all),
        "zorder_status_counts": dict(sorted(Counter(r["lock_status"] for r in z_all).items())),
        "zorder_population": {
            "mutants": len(in_pop),
            "tasks": len({r["task_id"] for r in in_pop}),
            "by_family_and_verdict": {
                k: dict(sorted(v.items())) for k, v in sorted(by_family_verdict.items())
            },
        },
        "zinv_zorder_rows": dict(sorted(zinv_readings.items())),
        "zinv_should_fail_rows": dict(sorted(zinv_should_fail.items())),
    }


def figure1(adj: dict) -> None:
    cc = adj["checker_candidates"]
    panels = [
        ("false_negative", "Should-pass operators: checker fails the mutant"),
        ("false_positive", "Should-fail operators: checker passes the mutant"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharex=True)
    for ax, (kind, title) in zip(axes, panels, strict=True):
        cand = cc[kind]["candidate_share"]["by_operator"]
        conf = cc[kind]["confirmed_share"]["by_operator"]
        ops = sorted(cand, key=lambda o: (-cand[o]["events"], -cand[o]["mutants"], o))
        n = len(ops)
        for i, op in enumerate(ops):
            y = n - 1 - i
            c = cand[op]
            k = conf[op]
            ax.plot([100 * c["low"], 100 * c["high"]], [y + 0.14] * 2, color=CAND, lw=1.4)
            ax.plot(100 * c["rate"], y + 0.14, "o", color=CAND, ms=4.5)
            ax.plot([100 * k["low"], 100 * k["high"]], [y - 0.14] * 2, color=CONF, lw=1.4)
            ax.plot(100 * k["rate"], y - 0.14, "D", mfc="white", mec=CONF, ms=4.2)
            ax.text(
                101.5,
                y,
                f"{c['events']}/{c['mutants']} ({c['tasks']} t)",
                va="center",
                fontsize=7,
                color=INK,
            )
        ax.set_yticks(range(n))
        ax.set_yticklabels(ops[::-1], fontsize=7)
        ax.set_xlim(-2, 100)
        ax.set_ylim(-0.7, n - 0.3)
        ax.set_xlabel("task-equal share of evaluable mutants (%)")
        ax.set_title(title, fontsize=8.5)
        ax.grid(axis="x", color="#e5e5e5", lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    handles = [
        plt.Line2D([], [], color=CAND, marker="o", lw=1.4, ms=4.5, label="candidate share"),
        plt.Line2D(
            [],
            [],
            color=CONF,
            marker="D",
            mfc="white",
            lw=1.4,
            ms=4.2,
            label="confirmed share (adjudicated, D82)",
        ),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, fontsize=8)
    fig.suptitle(
        "Candidate checker errors per operator, evaluable mutants outside probe-touched cells "
        "(95% task-cluster bootstrap)",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.07, 0.94, 0.95))
    fig.savefig(NOTE / "figures/fig1-operator-shares.svg", metadata={"Date": None})
    plt.close(fig)


def figure2(adj: dict, der: dict) -> None:
    status = der["zorder_status_counts"]
    fam = der["zorder_population"]["by_family_and_verdict"]
    fails = sum(v.get("fail", 0) for v in fam.values())
    passes = sum(v.get("pass", 0) for v in fam.values())
    dec = load(CONFIRM_SUMMARY)["decisions_by_group"]["fn_equiv"]
    both_accept = dec["accept/accept -> accept"]
    split = sum(v for k, v in dec.items() if "unresolved" in k)
    reading = adj["checker_candidates"]["false_negative"]["counts"]["by_audit_reading"]
    k2c_fail = load(K2)["k2c"]["by_offline_verdict"]["fail"]
    zr = der["zinv_zorder_rows"]
    zinv_pass = sum(v for k, v in zr.items() if k.endswith("raw=0.0|zinv=1.0"))
    cpf_fail = fam["compare_pptx_files"].get("fail", 0)
    tol_fail = fam.get("compare_pptx_files_tolerant", {}).get("fail", 0)

    stages = [
        (
            f"planned ({der['zorder_planned']})",
            [
                ("evaluable", status.get("evaluable", 0), CAND),
                ("null mutant fails", status.get("null_not_pass", 0), GREY),
                ("ambiguous label", status.get("ambiguous", 0), "#c9c9c9"),
                ("not admitted", status.get("not_admitted", 0), "#e0e0e0"),
            ],
        ),
        (
            f"evaluable ({fails + passes}), offline checker",
            [("fails", fails, CAND), ("passes", passes, "#c9c9c9")],
        ),
        (
            f"candidates ({fails}), two model raters",
            [("both accept", both_accept, CAND), ("split", split, GREY)],
        ),
        (
            f"candidates ({fails}), adjudicated (D82)",
            [
                ("confirmed", reading["confirmed"], CONF),
                ("label contradicted, gold-defect task", reading["label_contradicted"], GREY),
            ],
        ),
        (
            f"candidates ({fails}), in the VM (K2-C)",
            [("fail in both runs", k2c_fail["agree"], CAND), ("differ", k2c_fail["differ"], GREY)],
        ),
        (
            f"compare_pptx_files candidates ({cpf_fail}), zinv (G0)",
            [("zinv passes", zinv_pass, CAND), ("zinv fails", cpf_fail - zinv_pass, GREY)],
        ),
    ]
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    n = len(stages)
    for i, (label, segs) in enumerate(stages):
        y = n - 1 - i
        x = 0
        small = []
        for name, val, color in segs:
            if val < 6:
                small.append(f"{name} {val}")
            if val == 0:
                continue
            ax.barh(y, val, left=x, color=color, edgecolor="white", height=0.62)
            ax.text(
                x + val / 2,
                y,
                f"{name} {val}" if val >= 6 else str(val),
                ha="center",
                va="center",
                fontsize=7,
                color="white" if color in (CAND, CONF) else INK,
            )
            x += val
        text = label + (": " + "; ".join(small) if small else "")
        ax.text(x + 0.6, y, text, va="center", fontsize=7.2, color=INK)
    ax.set_yticks([])
    ax.set_xlim(0, 100)
    ax.set_xlabel("mutants of pptx.eq.zorder_nonoverlap")
    ax.set_title(
        f"The z-order equivalence mutants through each stage "
        f"(compare_pptx_files {cpf_fail}, compare_pptx_files_tolerant {tol_fail} candidates)",
        fontsize=9,
    )
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(NOTE / "figures/fig2-zorder-stages.svg", metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    (NOTE / "figures").mkdir(parents=True, exist_ok=True)
    (NOTE / "data").mkdir(parents=True, exist_ok=True)
    adj = load(ADJ)
    der = derived()
    (NOTE / "data/derived.json").write_text(json.dumps(der, indent=1, sort_keys=False) + "\n")
    figure1(adj)
    figure2(adj, der)


if __name__ == "__main__":
    main()
