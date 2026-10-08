"""S1a plan: caps under D22, the A0-derived rules, CPUs, draws, orders and engine arguments."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from harness.q2_stage1 import plan as P

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis"
CARD_PLAN = (
    ROOT / "program/evidence/2026-10-07/serving-throughput-probe-v2/overlay/plan-job-a-v2.json"
)
sys.path.insert(0, str(ROOT / "scripts"))
import render_q2_stage1_plan as renderer  # noqa: E402


@pytest.fixture(scope="module")
def inputs():
    return renderer.load_inputs(ROOT)


def test_concurrency_rows_and_cpu_feasibility():
    assert [P.a1_concurrency(n) for n in (40, 32, 24, 16, 8, 1)] == [20, 20, 20, 16, None, None]
    assert P.anchor_concurrency(40) == 32 and P.anchor_concurrency(24) == 24
    assert P.check_cpus([20], 1) == 122
    assert P.check_cpus([32], 1) == 176
    assert P.check_cpus([16], 1) == 104
    with pytest.raises(P.PlanError):
        P.check_cpus([20, 20], 2)  # two sizes at once: 244 CPUs
    with pytest.raises(P.PlanError):
        P.check_cpus([40], 1)  # ANC at V = 40: 212 CPUs
    with pytest.raises(P.PlanError):
        P.check_cpus([16, 16], 2)  # 208, the whole node


@pytest.mark.parametrize(
    ("anchor_runs", "a0b_runs", "cap", "total"),
    [(True, True, 91, 476), (False, True, 104, 476), (False, False, 111, 478)],
)
def test_remainder_rule_keeps_every_branch_under_8_gpu_hours(anchor_runs, a0b_runs, cap, total):
    pre = [P.CAP_MINUTES["O1"], P.CAP_MINUTES["A0a"]] + ([P.CAP_MINUTES["A0b"]] if a0b_runs else [])
    assert P.a1_cap_minutes(pre, anchor_runs, a0b_runs) == cap
    assert P.total_cap_minutes(pre, anchor_runs, cap) == total <= P.GPU_MINUTES_LIMIT - 2


def test_an_a0_repeat_is_paid_from_the_a1_caps():
    pre = [3, 25, 26, 25]  # A0a ran twice
    cap = P.a1_cap_minutes(pre, True)
    assert cap == 85 and P.total_cap_minutes(pre, True, cap) <= 478
    with pytest.raises(P.PlanError):
        P.a1_cap_minutes([3, 25], True, a0b_runs=False)


def test_a0_caps_hold_their_wave_before_usr1():
    need = P.check_a0_caps()
    assert need["A0a"] <= P.CAP_MINUTES["A0a"] - 3
    assert need["A0b"] <= P.CAP_MINUTES["A0b"] - 3
    with pytest.raises(P.PlanError):
        P.check_a0_caps(launch_min=10)


def test_k_rule_counts_usr1_launch_and_requeues():
    # The reviewer's case: a 100-minute job at the V = 16 high price gives 24, not 32.
    assert P.k_base(100, 6, 0.011512) == 24
    assert P.k_base(104, 6, P.PRICE_HIGH[20]) == 32
    assert P.k_base(91, 6, P.PRICE_HIGH[20]) == 24
    assert P.k_base(91, 6, 0.0137) == 16
    assert P.k_base(111, 3, 0.005, k_nstar=32) == 32  # never above K_N*
    c = P.c_a0a([600.0] * 20, 20)
    assert c == pytest.approx(600 / 3600 / 20)
    assert P.c_proj(20, c) == P.PRICE_HIGH[20]
    assert P.c_proj(20, 0.012) == pytest.approx(0.015)
    with pytest.raises(P.PlanError):
        P.c_a0a([], 20)


def test_anchor_size_rule():
    assert P.anchor_tasks(40, 6, 8.0) == 96  # d floored at the card's central slot
    assert P.anchor_tasks(40, 6, 13.17) == 64
    assert P.anchor_tasks(24, 6, 8.0) == 72
    assert P.anchor_tasks(16, 6, 8.0) == 48  # below 58: UNAVAILABLE
    assert P.anchor_dispatch_allowed(20.0, 10.0)
    assert not P.anchor_dispatch_allowed(14.0, 10.0)
    assert P.fill_allowed(0.009, 60) and not P.fill_allowed(0.009, 30)


def test_freeze_constants_branches():
    slots = [640.0] * 20
    pre = [3, 25, 26]
    fc = P.freeze_constants(
        n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=pre,
        anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0,
    )  # fmt: skip
    assert fc.anchor_runs and fc.anchor_tasks == 96 and fc.a1_cap_min == 91 and fc.k_base == 24
    assert fc.total_cap_min <= 478
    off = P.freeze_constants(
        n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=[3, 25],
        anchor_available=False,
    )  # fmt: skip
    assert not off.anchor_runs and off.a1_cap_min == 111 and off.k_base == 32
    with pytest.raises(P.PlanError, match="floor 32"):
        P.freeze_constants(
            n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=pre,
            anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0, k_floor=32,
        )  # fmt: skip
    with pytest.raises(P.PlanError, match="floor is 24"):
        P.freeze_constants(
            n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=[3, 25],
            anchor_available=False, k_floor=16,
        )  # fmt: skip
    small = P.freeze_constants(
        n_star=16, a0a_slot_seconds=[700.0] * 16, launch_a0a_min=4, prefreeze_caps=pre,
        anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0,
    )  # fmt: skip
    assert not small.anchor_runs and small.anchor_tasks == 0 and small.a1_cap_min == 104
    with pytest.raises(P.PlanError, match="floor"):
        P.freeze_constants(
            n_star=40, a0a_slot_seconds=[1100.0] * 20, launch_a0a_min=6, prefreeze_caps=pre,
            anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0,
        )  # fmt: skip
    with pytest.raises(P.PlanError, match="N"):
        P.freeze_constants(
            n_star=8, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=pre,
            anchor_available=False,
        )  # fmt: skip


def test_prices_equal_the_cost_analysis():
    cost = json.loads((BUNDLE / "cost_s1a.json").read_text())["s1a_v2"]
    for v in (16, 20):
        assert cost["prices"][str(v)]["central"] == P.PRICE_CENTRAL[v]
        assert cost["prices"][str(v)]["high"] == P.PRICE_HIGH[v]
    assert cost["anchor_slot_min"] == P.ANCHOR_SLOT_MIN
    assert cost["a0a_slot_high_min"] == P.A0A_SLOT_HIGH_MIN
    assert cost["caps"] == P.CAP_MINUTES


@pytest.mark.parametrize("k", [16, 24, 32])
def test_task_draw_reproduces_the_bundle(inputs, k):
    pool = P.task_pool(inputs["confirm_ids"])
    draw = P.draw_tasks(pool, inputs["domain"], k)
    bundle = json.loads((BUNDLE / f"task-draw-K{k}.json").read_text())
    assert {key: bundle[key] for key in draw} == draw
    assert bundle["splits_sha256"] == inputs["splits_sha256"]
    big = P.draw_tasks(pool, inputs["domain"], 32)
    assert set(draw["base"]) <= set(big["base"])


def test_anchor_order_is_a_stratified_permutation(inputs):
    pool = P.task_pool(inputs["confirm_ids"])
    order = P.anchor_order(pool, inputs["domain"])
    assert sorted(order) == pool and len(order) == 116
    counts = Counter(inputs["domain"][t] for t in pool)
    for n in (58, 64, 72, 96):
        got = Counter(inputs["domain"][t] for t in order[:n])
        for d, c in counts.items():
            assert abs(got[d] - c * n / 116) < 1.0 + 1e-9


def test_dev_tasks_filter_then_take_first(inputs):
    ok = dict.fromkeys(inputs["dev_ids"], True)
    first = P.dev_tasks(inputs["dev_ids"], ok, 5)
    ok[first[0]] = False
    again = P.dev_tasks(inputs["dev_ids"], ok, 5)
    assert again[:4] == first[1:] and first[0] not in again
    assert not set(first) & set(inputs["confirm_ids"])
    with pytest.raises(P.PlanError):
        P.dev_tasks(inputs["dev_ids"], {}, 4)


def test_orders_cover_each_cell_once_and_differ_by_block(inputs):
    pool = P.task_pool(inputs["confirm_ids"])
    draw = P.draw_tasks(pool, inputs["domain"], 24)
    orders = P.episode_orders(draw)
    b1 = orders["S1:9B:b1"]
    assert sorted(map(tuple, b1)) == sorted((t, h) for t in draw["base"] for h in P.HARNESSES)
    assert b1 != orders["S1:9B:b2"] and b1 != orders["S2:9B:b1"]
    assert len(orders["S2:4B:x01.2"]) == 16
    assert P.size_order() == P.size_order() and sorted(P.size_order()) == ["4B", "9B"]


def test_engine_argv_is_the_cards_and_the_anchor_variant():
    card = json.loads(CARD_PLAN.read_text())["phases"][0]["argv"]
    ours = P.engine_argv("/model-cache/cotcodec-models/qwen3.5-9b", "probe-model")
    assert ours == card
    anchor = P.engine_argv("/m", "s", anchor=True)
    assert anchor[anchor.index("--max-model-len") + 1] == "32768"
    assert '"count":4' in anchor[anchor.index("--limit-mm-per-prompt") + 1]
    assert anchor[-1] == "--trust-remote-code" and "--trust-remote-code" not in ours
    assert P.sampling("H-GA") == P.sampling("H-OSW-fixed")
    assert P.sampling("H-GA")["temperature"] == 0.0 and P.sampling("H-GA")["top_k"] == -1


def test_jobs_are_sequential_and_paired(inputs):
    jobs = P.session_jobs(40, 91, anchor_runs=True)
    names = [j["job"] for j in jobs]
    order = P.size_order()
    assert names == ["O2", "ANC"] + [f"A1-{z}-S1" for z in order] + [f"A1-{z}-S2" for z in order]
    for job in jobs[1:]:
        assert job["vm_minutes"] == job["gpu_minutes"] + 10
        assert job["co_running_cpus"] <= P.CPU_LIMIT
    assert P.gpu_sbatch_time(91) == "01:31:00"


def test_renderer_draft_and_freeze_modes(tmp_path):
    out = tmp_path / "plan.json"
    script = ROOT / "scripts/render_q2_stage1_plan.py"
    run = subprocess.run(
        [sys.executable, str(script), "--out", str(out)], capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    plan = json.loads(out.read_text())
    assert plan["status"] == "draft" and len(plan["base"]) == 32
    assert plan["plan_sha256"] == run.stdout.strip()
    again = subprocess.run(
        [sys.executable, str(script), "--out", str(out)], capture_output=True, text=True
    )
    assert again.returncode != 0
    constants = tmp_path / "c.json"
    constants.write_text(
        json.dumps(
            {
                "n_star": 40, "a0a_slot_seconds": [640.0] * 20, "launch_a0a_min": 4,
                "prefreeze_caps": [3, 25, 26], "anchor_available": True,
                "launch_a0b_min": 5, "longest_a0b_slot_min": 10.0,
            }
        )
    )  # fmt: skip
    dev = tmp_path / "dev.json"
    dev.write_text(json.dumps(dict.fromkeys(renderer.load_inputs(ROOT)["dev_ids"], True)))
    frozen = tmp_path / "frozen.json"
    run = subprocess.run(
        [sys.executable, str(script), "--constants", str(constants), "--dev-setup", str(dev),
         "--out", str(frozen)], capture_output=True, text=True,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    plan = json.loads(frozen.read_text())
    assert plan["constants"]["k_base"] == 24 and len(plan["base"]) == 24
    assert len(plan["anchor_tasks"]) == 96 and len(plan["dev_tasks_a0a"]) == 5
    assert set(plan["dev_tasks_a0b"]) <= set(plan["dev_tasks_a0a"])
    assert all(t in plan["anchor_order"] for t in plan["flagged_tasks"])
