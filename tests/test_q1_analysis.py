"""Ladder composition and Stage 0 metrics on synthetic journal rows (needs scipy)."""

from __future__ import annotations

import pytest

pytest.importorskip("scipy")

from harness.q1 import analysis  # noqa: E402
from harness.q1.schema import make_verdict_row  # noqa: E402


def _row(
    kernel: str,
    gate: str,
    verdict: str,
    config: str = "native/seed-42",
    policy: str = "torch-default",
    gpu: float = 1.0,
    item: str | None = None,
) -> dict:
    return make_verdict_row(
        kernel_id=kernel,
        gate=gate,
        config_id=config,
        verdict=verdict,
        tf32_policy=policy,
        gpu_seconds=gpu,
        details={"item_key": f"{kernel}|{item or gate}|seed-42"},
        seed=42,
    )


def _kernel(kernel: str, gates: dict[str, str], audit: dict[str, str]) -> list[dict]:
    rows = [_row(kernel, g, gates[g]) for g in ("a", "b1", "b2") if g in gates]
    for family in ("c1", "c2", "c3", "c_1e-2", "c_kbv_raw"):
        rows.append(
            _row(kernel, family, gates.get(family, "accept"), "aggregate", item="c", gpu=2.0)
        )
    for channel in ("A1", "A2", "A3"):
        for policy in analysis.POLICIES:
            rows.append(_row(kernel, channel, audit.get(channel, "accept"), "aggregate", policy))
    rows.append(_row(kernel, "A4", audit.get("A4", "accept"), "in-process", "not-applicable"))
    return rows


def test_ladder_and_tiers() -> None:
    rows = _kernel(
        "m1", {"a": "accept", "b1": "error", "b2": "accept", "c2": "reject"}, {"A3": "reject"}
    )
    rows += _kernel("m2", {"a": "accept", "b1": "accept", "b2": "accept"}, {"A3": "refuse"})
    rows.append(_row("m3", "a", "timeout", "item/seed-42"))
    composed = analysis.compose(rows)
    m1 = composed["m1"]
    assert m1["ladder"]["b"] == "accept" and m1["b_fail_open"] == ["b1"]
    assert m1["ladder"]["c"] == "reject"
    assert m1["tiers"]["tf32-admissible"]["G"] == "reject"
    m2 = composed["m2"]["tiers"]["tf32-admissible"]
    assert m2["G"] == "accept" and m2["G-strict"] == "reject"
    assert composed["m3"]["ladder"]["a"] == "reject"  # a timeout is a rejection


def test_metrics_ms_far_frr() -> None:
    rows = []
    table = {}
    for i in range(10):  # witnessed mutants: a misses 4, c catches all
        kernel = f"mut{i}"
        table[kernel] = {"kind": "mutant", "problem_id": f"L1/{i % 3}_P", "family": "boundary"}
        a = "accept" if i < 4 else "reject"
        rows += _kernel(
            kernel, {"a": a, "b1": "accept", "b2": "accept", "c1": "reject"}, {"A1": "reject"}
        )
    for i in range(5):  # correct substrates
        kernel = f"sub{i}"
        table[kernel] = {"kind": "substrate", "problem_id": f"L1/{i}_P", "family": None}
        rows += _kernel(
            kernel,
            {"a": "accept", "b1": "accept", "b2": "accept", "c3": "reject" if i == 0 else "accept"},
            {},
        )
    result = analysis.metrics(analysis.compose(rows), table, resamples=200)
    assert result["counts"]["witnessed"] == 10 and result["counts"]["correct_substrates"] == 5
    assert result["gates"]["a"]["MS"]["k"] == 6 and result["gates"]["a"]["FAR"] == pytest.approx(
        0.4
    )
    assert result["gates"]["c"]["MS"]["rate"] == 1.0
    assert result["gates"]["c"]["FRR"]["k"] == 1 and result["gates"]["a"]["FRR"]["k"] == 0
    assert result["gates"]["a"]["FA_share_uninterpreted"]["rate"] == 1.0
    assert result["MS_by_family"]["boundary"]["a"]["k"] == 6


def test_cost_ratio_uses_per_kernel_sums() -> None:
    rows = _kernel("k", {"a": "accept", "b1": "accept", "b2": "accept"}, {})
    rows.append(_row("k", "c_extra", "accept", "x", gpu=0.0, item="c"))
    summary = analysis.cost(rows)
    assert summary["ladder"]["b_median"] == pytest.approx(3.0)
    assert summary["ladder"]["c_median"] == pytest.approx(13.0)  # five c rows of 2.0 GPU-s


def test_splits_are_seeded_and_disjoint() -> None:
    problems = [f"L1/{i}_P" for i in range(9)]
    cal, ev = analysis.calibration_split(problems)
    assert len(cal) == 5 and len(ev) == 4 and not set(cal) & set(ev)
    assert analysis.calibration_split(reversed(problems)) == (cal, ev)
    dev, test = analysis.mutant_split([f"m{i}" for i in range(7)])
    assert len(dev) == 3 and len(test) == 4 and not set(dev) & set(test)
