"""Pilot cost card: GPU apportionment, per-kernel totals and the projection (pure Python)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from harness.q1 import cost_card as cc


def _item(start: float, end: float, **extra) -> dict:
    return {
        "start": start,
        "end": end,
        "final": True,
        "verdicts": Counter(),
        "reasons": Counter(),
        **extra,
    }


def test_charge_splits_overlaps_and_leaves_idle_time_uncharged() -> None:
    items = [_item(0.0, 10.0), _item(5.0, 15.0), _item(20.0, 22.0)]
    cc.charge(items)
    assert [round(i["gpu_seconds"], 6) for i in items] == [7.5, 7.5, 2.0]


def _write_job(root: Path, rows: list[dict]) -> Path:
    q1 = root / "q1"
    (q1 / "scoring").mkdir(parents=True)
    (q1 / "phases.json").write_text(json.dumps({"phases": []}))
    (q1 / "scoring" / "journal.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (q1 / "scoring" / "items.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "kernel_id": r["kernel_id"],
                    "gate": r["gate"],
                    "seed": r["seed"],
                    "problem_id": "L1/19_ReLU",
                }
            )
            + "\n"
            for r in rows
        )
    )
    return q1


def test_kernel_seed_costs_need_every_scoring_gate(tmp_path: Path) -> None:
    rows = []
    t = 0.0
    for kernel in ("k1", "k2"):
        for gate in cc.SCORING_GATES:
            if kernel == "k2" and gate == "A5":
                continue  # incomplete kernel
            rows.append(
                {
                    "kernel_id": kernel,
                    "gate": gate,
                    "seed": 42,
                    "attempt": 1,
                    "verdict": "accept",
                    "config_id": "x",
                    "details": {
                        "item_key": f"{kernel}|{gate}|seed-42",
                        "item_final": True,
                        "item_started_at": t,
                        "item_ended_at": t + 2.0,
                        "item_wall_seconds": 2.0,
                        "item_exclusive": True,
                    },
                }
            )
            t += 3.0
    job = cc.load_job(_write_job(tmp_path, rows))
    costs = cc.kernel_seed_costs(job["items"], {})
    assert [r["kernel_id"] for r in costs] == ["k1"]
    assert costs[0]["total"] == pytest.approx(30.0)
    assert costs[0]["b_marginal"] == pytest.approx(4.0)
    assert costs[0]["cost_class"] == "L1-exclusive"
    assert cc.gate_stats(job["items"])["a"]["gpu_seconds"]["median"] == 2.0


def test_projection_counts_and_borrowing() -> None:
    counts = {
        "evaluation_substrates": [
            {
                "problem_id": "L1/19_ReLU",
                "exclusive": True,
                "hack_controls": 2,
                "cpu_distinct_by_family": {"arithmetic": 30, "boundary": 2},
            },
            {
                "problem_id": "L2/12_Gemm",
                "exclusive": False,
                "hack_controls": 0,
                "cpu_distinct_by_family": {"indexing": 5},
            },
        ],
        "identity_controls": [{"problem_id": "L2/12_Gemm", "exclusive": False}],
        "adversarial_controls": 0,
        "hack_emulating_mutant_controls": 0,
    }
    stage = cc.stage0_kernel_counts(counts, cap=10, survival=1.0)
    assert stage["mutants_per_family"] == {"arithmetic": 8, "boundary": 2, "indexing": 5}
    assert stage["per_class"] == {"L1-exclusive": 13, "L2-shared": 7}
    seconds, borrowed = cc.scoring_seconds(stage["per_class"], {"L1-exclusive": 10.0})
    assert borrowed == ["L2-shared"] and seconds == pytest.approx((13 + 7) * 3 * 10.0)
    assert cc.half_width(100) == pytest.approx(0.1109, abs=1e-3)


def test_size_model_fits_and_falls_back_to_the_per_draw_slope() -> None:
    def item(gate: str, problem: str, seconds: float) -> dict:
        return {"final": True, "gate": gate, "problem_id": problem, "gpu_seconds": seconds}

    small, big = "L2/74_ConvTranspose3d_LeakyReLU_Multiply_LeakyReLU_Max", "L1/19_ReLU"
    gb = 6442450944 / 1e9
    items = [item("a", small, 5.0), item("a", small, 5.0), item("a", big, 5.0 + 10.0 * gb)]
    items += [item("A2", small, 4.0)]
    fits = cc.fit_item_costs(items)
    assert fits["a"]["method"] == "fit" and fits["a"]["beta"] == pytest.approx(10.0, rel=1e-2)
    assert fits["A2"]["method"] == "per-draw-slope"
    assert fits["A2"]["beta"] == pytest.approx(10.0 / 5 * 7, rel=1e-2)
    counts = {
        "evaluation_substrates": [
            {
                "problem_id": big,
                "exclusive": True,
                "hack_controls": 0,
                "cpu_distinct_by_family": {"arithmetic": 4},
            },
        ],
        "identity_controls": [],
        "adversarial_controls": 0,
        "hack_emulating_mutant_controls": 0,
    }
    full = cc.project_scoring(counts, fits, cap=40, survival=1.0)
    trimmed = cc.project_scoring(counts, fits, cap=2, survival=1.0, mutant_seeds=1)
    assert full["kernels"] == {"substrate": 1, "mutant": 4}
    assert trimmed["kernels"] == {"substrate": 1, "mutant": 2}
    assert trimmed["gpu_hours"] < full["gpu_hours"]
    assert set(full["missing_gates"]) == set(cc.SCORING_GATES) - {"a", "A2"}
