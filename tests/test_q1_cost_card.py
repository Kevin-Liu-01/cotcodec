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
                "substrate_id": "s1-inductor-L1-19_ReLU",
                "source_kind": "inductor",
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
    assert full["n_eval_independent"] == 1
    shared = cc.project_scoring(counts, fits, cap=40, survival=1.0, scope="shared")
    assert shared["gpu_hours"] == 0 and shared["n_eval_independent"] == 0


def _job_item(key: str, gpu: float, wall: float, verdicts: dict, phase: str = "scoring") -> dict:
    kernel, gate, seed = key.rsplit("|", 2)
    return {
        "phase": phase,
        "item_key": key,
        "kernel_id": kernel,
        "gate": gate,
        "final": True,
        "gpu_seconds": gpu,
        "wall": wall,
        "verdicts": Counter(verdicts),
    }


def test_pair_jobs_reports_ratios_and_verdict_differences() -> None:
    base = [
        _job_item("k|a|seed-42", 2.0, 8.0, {"accept": 1}),
        _job_item("k|A4|seed-42", 4.0, 8.0, {"accept": 2, "error": 1}),
        _job_item("only-base|a|seed-42", 1.0, 4.0, {"accept": 1}),
    ]
    other = [
        _job_item("k|a|seed-42", 1.0, 12.0, {"accept": 1}),
        _job_item("k|A4|seed-42", 1.0, 12.0, {"accept": 3}),
    ]
    paired = cc.pair_jobs(base, other)
    assert paired["items_in_both"] == 2 and paired["only_base"] == 1
    assert paired["per_gate"]["a"]["gpu_seconds_ratio_median"] == 0.5
    assert paired["per_gate"]["a"]["wall_ratio_median"] == 1.5
    assert paired["gpu_seconds_ratio_total"] == pytest.approx(2.0 / 6.0, abs=1e-3)
    assert [d["item_key"] for d in paired["verdict_differences"]] == ["k|A4|seed-42"]


def test_censored_items_are_recovered_as_lower_bounds(tmp_path: Path) -> None:
    import os

    phase = tmp_path / "q1" / "scoring"
    (phase / "items" / "q1item-a").mkdir(parents=True)
    (phase / "items" / "q1item-b").mkdir(parents=True)
    done = {"details": {"item_key": "k|a|seed-42"}}
    (phase / "journal.jsonl").write_text(json.dumps(done) + "\n")
    (phase / "items" / "q1item-a" / "item.json").write_text(
        json.dumps({"item_key": "k|a|seed-42", "gate": "a", "exclusive": True})
    )
    killed = phase / "items" / "q1item-b" / "item.json"
    killed.write_text(
        json.dumps({"item_key": "k|c|seed-42", "gate": "c", "exclusive": True, "problem_id": "p"})
    )
    (phase / "summary.json").write_text("{}")
    os.utime(killed, (1000.0, 1000.0))
    os.utime(phase / "summary.json", (1675.0, 1675.0))
    (censored,) = cc.censored_items(tmp_path / "q1")
    assert censored["item_key"] == "k|c|seed-42"
    assert censored["gpu_seconds_lower_bound"] == 675.0


def test_trimmed_projection_keeps_every_family_and_reaches_the_frr_units() -> None:
    fits = {gate: {"alpha": 1.0, "beta": 10.0} for gate in cc.SCORING_GATES}
    small = "L2/74_ConvTranspose3d_LeakyReLU_Multiply_LeakyReLU_Max"
    big = "L1/19_ReLU"

    def row(sid: str, problem: str, nbytes: int, exclusive: bool, fams: dict) -> dict:
        return {
            "substrate_id": sid,
            "problem_id": problem,
            "source_kind": "inductor",
            "native_input_bytes": nbytes,
            "exclusive": exclusive,
            "hack_controls": 4,
            "cpu_distinct_by_family": fams,
        }

    counts = {
        "evaluation_substrates": [
            row("s1-a", small, 16_777_216, False, {"arithmetic": 200, "boundary": 3}),
            row("s1-b", big, 6_442_450_944, True, {"arithmetic": 50}),
        ],
        "identity_controls": [
            {"problem_id": small, "exclusive": False},
            {"problem_id": big, "exclusive": True},
        ],
        "adversarial_controls": 3,
    }
    rule = {**cc.TRIM_RULE, "frr_min_units": 2, "family_quota_test": 10, "family_quota_dev": 2}
    out = cc.project_trimmed(counts, fits, survival=1.0, rule=rule)
    assert out["n_eval_independent"] == 2 and out["frr_extra_substrates"] == ["s1-b"]
    fam = out["mutants_per_family"]
    assert fam["arithmetic"]["test"] == 10 and fam["arithmetic"]["dev"] == 2
    assert fam["boundary"]["test"] == 2  # fewer than the quota: all of the frame's half
    assert out["kernels"]["frr-substrate-replicate-42"] == 1
    halved = cc.project_trimmed(
        counts, fits, survival=1.0, rule=rule, factors=dict.fromkeys(cc.SCORING_GATES, 0.5)
    )
    assert halved["gpu_hours"] < out["gpu_hours"]
    assert (
        halved["gpu_hours_by_role"]["frr-substrate-replicate-42"]
        == out["gpu_hours_by_role"]["frr-substrate-replicate-42"]
    )  # exclusive problems are not scaled by the concurrency factor
