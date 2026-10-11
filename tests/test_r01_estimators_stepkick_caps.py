"""R01 v2: the registered estimator and readings, the two-stage model, and the cap arithmetic."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np

from harness.r01 import caps, estimators, stepkick

ROOT = Path(__file__).resolve().parents[1]
DIGESTS = ROOT / "program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"
A1 = ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"


def test_bounds_and_readings():
    tasks = [f"t{i}" for i in range(113) for _ in range(2)]
    zeros = estimators.bounds(tasks, [0] * 226)
    assert (
        zeros["estimate"] == 0 and zeros["hi"] == 0 and zeros["n"] == 226 and zeros["tasks"] == 113
    )
    assert estimators.read_text(zeros["lo"], zeros["hi"]) == "INERT"
    half = estimators.bounds(tasks, [1, 0] * 113)
    assert estimators.read_text(half["lo"], half["hi"]) == "SUFFICIENT"
    assert estimators.read_ir(half["lo"], half["hi"]) == "MAJOR"
    assert estimators.read_ir(0.0, 0.11) == "MINOR" and estimators.read_ir(0.03, 0.12) == "PARTIAL"
    assert estimators.bounds(tasks, [1, 0] * 113) == half  # seeded


def test_det_threshold_matches_wave_1_at_320_and_reads_226():
    assert estimators.det_threshold(320) == 7
    k226 = estimators.det_threshold(226)
    assert estimators.read_det(0, 226)["reading"] == "DET_OK"
    assert estimators.read_det(1, 226)["reading"] == "DET_NEAR"
    assert estimators.read_det(k226, 226)["reading"] == "DET_UNATTAINABLE"


def test_joint_text_reading():
    assert (
        estimators.joint_text({"s": "SUFFICIENT", "c": "SUFFICIENT", "o": "PARTIAL"}) == "REDUNDANT"
    )
    assert estimators.joint_text({"s": "SUFFICIENT", "c": "INERT", "o": "INERT"}) == "SINGLE_SOURCE"
    assert estimators.joint_text({"s": "INERT", "c": "INERT", "o": "INERT"}) == "NEITHER"
    assert estimators.joint_text({"s": "SUFFICIENT", "c": "PARTIAL", "o": "INERT"}) == "MIXED"


def test_compare_pairs_cells_and_voids_on_missing_data():
    ref = [
        {"task": f"t{i}", "pair": 1, "step": 1, "content_sha256": "a", "ir_sha256": "x"}
        for i in range(40)
    ]
    other = [dict(r, content_sha256="b" if i % 2 else "a") for i, r in enumerate(ref)]
    cmp = estimators.compare(ref, other)
    assert cmp["n"] == 40 and sum(cmp["text"]) == 20 and sum(cmp["ir"]) == 0 and not cmp["void"]
    cmp = estimators.compare(ref, other[:37])
    assert cmp["missing"] == 3 and cmp["void"]
    reading = estimators.cell_reading(estimators.compare(ref, other))
    assert reading["text"]["reading"] == "SUFFICIENT" and reading["ir"]["reading"] == "MINOR"


def test_validation_reading():
    s1a_tasks = [f"t{i}" for i in range(113) for _ in range(2)]
    s1a_text = [1] * 205 + [0] * 21
    s1a_ir = [1] * 79 + [0] * 147
    same = estimators.validation(s1a_tasks, s1a_text, s1a_ir, s1a_tasks, s1a_text, s1a_ir)
    assert same["reading"] == "VAL_PASS"
    low_ir = [1] * 20 + [0] * 206
    off = estimators.validation(s1a_tasks, s1a_text, low_ir, s1a_tasks, s1a_text, s1a_ir)
    assert off["reading"] == "VAL_FAIL"


def test_interaction():
    assert estimators.interaction(0.5, 0.5, 0.0) == 0.0
    assert estimators.interaction(0.5, 0.5, 0.5) < 0


def test_stepkick_recovers_known_rates_and_freezes_without_onsets():
    rng = np.random.default_rng(0)
    pairs = []
    for i in range(4000):
        t = 1 if rng.random() < 0.9 else (2 if rng.random() < 0.9 else None)
        u = None
        if t is not None:
            if rng.random() < 0.35:
                u = t
            else:
                for k in range(t + 1, 16):
                    if rng.random() < 0.3:
                        u = k
                        break
        pairs.append(stepkick.Pair(task=f"t{i}", t=t, u=u, end=15, discordant=0))
    params, _ = stepkick.fit(pairs)
    assert (
        abs(params.kappa[0] - 0.9) < 0.02
        and abs(params.pi - 0.35) < 0.03
        and abs(params.rho - 0.3) < 0.02
    )
    frozen = stepkick.Params(kappa=[0.0] * 15, pi=0.3, rho=0.3, tau=[0.0] * 14 + [1.0])
    assert stepkick.survival(frozen)["N"] == 1.0


def test_stepkick_reproduces_s1a_4b_osw_in_sample():
    with gzip.open(DIGESTS, "rt") as handle:
        rows = [json.loads(x) for x in handle]
    recs = [json.loads(x) for x in A1.read_text().splitlines()]
    groups = {
        f"{z}/{h}": stepkick.pairs_from(rows, recs, z, h)
        for z in ("4B", "9B")
        for h in ("H-OSW-fixed", "H-GA")
    }
    v = stepkick.validate(groups, "4B/H-OSW-fixed")
    assert v["pairs"] == 226 and v["D_w_observed"] == round(27 / 226, 4)
    assert v["max_abs_gap"] < 0.03 and abs(v["D_w_model"] - v["D_w_observed"]) < 0.005
    assert v["observed_identical_through"][0] == round(1 - 79 / 226, 4)
    p = v["params"]
    live = stepkick.predict(205 / 226, 79 / 226, 19 / 21, rho=p["rho"], tau=p["tau"], q=v["q"])
    weaker = stepkick.predict(0.3, 0.02, 0.3, rho=p["rho"], tau=p["tau"], q=v["q"])
    assert abs(live["D_w"] - v["D_w_observed"]) < 0.01 and weaker["D_w"] < live["D_w"]


def test_caps_formula_and_loaded_simulation_exceeds_one_lanes_mean(monkeypatch):
    monkeypatch.setattr(caps, "SIM_DRAWS", 2000)
    assert caps.cap_minutes(0, 1) == 5 and caps.cap_minutes(600, 2) == 3 + 4 + 13
    cost = caps.StepCost(1, 3400.0, 2.0, 2.6, tuple([1.8, 2.0, 2.2, 2.6] * 50))
    costs = {1: cost}
    sim = caps.simulate_loaded(costs, {1: 320}, 4, draws=2000)
    think = caps.think_mean(costs, {1: 320})
    one_lane_mean = 4 * 16 * (2.0 + think)
    assert sim.mean() > one_lane_mean  # the max over 20 lanes, not one lane's mean
    assert np.quantile(sim, 0.95) > sim.mean()
    row = caps.Job("J3", "E-s1a", "B1", loaded_counts={1: 320}, loaded_passes=4).row(costs)
    assert row["cap_min"] >= caps.cap_minutes(np.quantile(sim, 0.95))
