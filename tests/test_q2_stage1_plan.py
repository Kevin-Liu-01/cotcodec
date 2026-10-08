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


def turn(truncated: bool = False, tool_call: bool = True, *step_s: float) -> dict:
    return {"truncated": truncated, "complete_tool_call": tool_call,
            "executed": [{"op": "click", "timing_s": {"total": t}} for t in step_s]}  # fmt: skip


GATES = P.a0a_gates([{"harness": h, "steps": [turn(False, True, 2.0)]} for h in P.HARNESSES], 2.71)


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
            a0a_gates=GATES,
        n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=pre,
        anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0, k_floor=24,
    )  # fmt: skip
    assert fc.anchor_runs and fc.anchor_tasks == 96 and fc.a1_cap_min == 91 and fc.k_base == 24
    assert fc.total_cap_min <= 478 and fc.k_floor == 24
    off = P.freeze_constants(
            a0a_gates=GATES,
        n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=[3, 25],
        anchor_available=False,
    )  # fmt: skip
    assert not off.anchor_runs and off.a1_cap_min == 111 and off.k_base == 32
    assert off.k_floor == 32
    with pytest.raises(P.PlanError, match="floor 32"):  # the default: item 18 not signed
        P.freeze_constants(
            a0a_gates=GATES,
            n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=pre,
            anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0,
        )  # fmt: skip
    with pytest.raises(P.PlanError, match="floor is 24"):
        P.freeze_constants(
            a0a_gates=GATES,
            n_star=40, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=[3, 25],
            anchor_available=False, k_floor=16,
        )  # fmt: skip
    # N* = 16: A0b ran but n = 48 < 58, so the anchor does not run and the floor is 32
    # even with k_floor=24; V = 16's high price cannot reach 32 in 104 minutes.
    for floor in (24, 32):
        with pytest.raises(P.PlanError, match="floor 32 .the anchor does not run"):
            P.freeze_constants(
            a0a_gates=GATES,
                n_star=16, a0a_slot_seconds=[700.0] * 16, launch_a0a_min=4, prefreeze_caps=pre,
                anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0,
                k_floor=floor,
            )  # fmt: skip
    with pytest.raises(P.PlanError, match="floor"):
        P.freeze_constants(
            a0a_gates=GATES,
            n_star=40, a0a_slot_seconds=[1100.0] * 20, launch_a0a_min=6, prefreeze_caps=pre,
            anchor_available=True, launch_a0b_min=5, longest_a0b_slot_min=10.0, k_floor=24,
        )  # fmt: skip
    with pytest.raises(P.PlanError, match="N"):
        P.freeze_constants(
            a0a_gates=GATES,
            n_star=8, a0a_slot_seconds=slots, launch_a0a_min=4, prefreeze_caps=pre,
            anchor_available=False,
        )  # fmt: skip


def test_unanchored_floor_is_32_at_the_cards_high_slot():
    """The branch S1a is in (anchor unavailable before A0b, T_A1 = 111): an A0a slot at the
    card's high value (743.12 s at V = 20) prices K_base at 24, below the floor of 32, so the
    draft goes back to review; K = 32 needs a mean A0a slot of at most about 728 s."""
    common = dict(n_star=40, launch_a0a_min=6, prefreeze_caps=[3, 25], anchor_available=False,
                  a0a_gates=GATES)  # fmt: skip
    for floor in (24, 32):  # no k_floor lowers the unanchored floor
        with pytest.raises(P.PlanError, match="K_base 24 is below the floor 32"):
            P.freeze_constants(a0a_slot_seconds=[743.12] * 20, k_floor=floor, **common)
    fc = P.freeze_constants(a0a_slot_seconds=[728.0] * 20, **common)
    assert fc.k_base == 32 and fc.k_floor == 32 and fc.a1_cap_min == 111
    with pytest.raises(P.PlanError, match="back to review"):
        P.freeze_constants(a0a_slot_seconds=[729.0] * 20, **common)


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


def a0a_run(tmp: Path, *, seconds=640.0, start=10_000.0, first=10_300.0, statuses=None,
            truncated_steps=0) -> tuple[Path, Path]:  # fmt: skip
    """A finished A0a lane run directory and its GPU job's bridge directory: V = 20 slots
    from ``plan.a0a_slots``, each scored after ``seconds`` of slot occupancy unless
    ``statuses`` (slot index -> list of attempt statuses) says otherwise."""
    inputs = renderer.load_inputs(ROOT)
    slots = P.a0a_slots(inputs["dev_ids"], P.dev_setup_ok(P.load_setup_check(ROOT)), 20)
    run = tmp / "run"
    (run / "episodes").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"purpose": "a0a", "vm": {"concurrency": 20},
                                                   "slots": slots}))  # fmt: skip
    rows = []
    for i, slot in enumerate(slots):
        for attempt, status in enumerate((statuses or {}).get(i, ["scored"]), start=1):
            rows.append({**slot, "attempt": attempt, "status": status,
                         "host": {"slot_occupancy_s": seconds + i}})  # fmt: skip
            out = run / "episodes" / f"{slot['slot'].replace(':', '_')}.a{attempt}"
            out.mkdir()
            steps = [turn(k < truncated_steps, k >= truncated_steps, 2.0) for k in range(5)]
            (out / "steps.jsonl").write_text("".join(json.dumps(t) + "\n" for t in steps))
    (run / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (run / "lane-receipt.json").write_text(json.dumps(
        {"gpu_job": {"job_id": "77", "start_epoch": start, "time_limit_min": 25},
         "first_dispatch": first, "t_end": start + 1400}))  # fmt: skip
    bridge = tmp / "bridge"
    bridge.mkdir()
    (bridge / "stopped.json").write_text(json.dumps({"t_first_request": first + 75}))
    return run, bridge


def test_a0a_measurements_come_from_the_records(tmp_path):
    """Section 6.2: c_A0a's slots, L_A0a (Slurm start to the first dispatch) and both gates
    over the same V episodes, all from A0a's records; nothing typed."""
    run, bridge = a0a_run(tmp_path / "ok", statuses={3: ["infrastructure", "scored"]})
    got = P.a0a_measurements(run, bridge, action_path_step_p95_s=2.71)
    assert len(got["a0a_slot_seconds"]) == 20 and got["a0a_slot_seconds"][0] == 640.0
    assert got["launch_a0a_min"] == 5.0  # (10,300 - 10,000) / 60
    assert got["measured"]["launch_to_first_request_min"] == 6.25
    assert got["a0a_gates"]["problems"] == [] and got["a0a_gates"]["turns"]["H-GA"] == 50
    assert set(got["measured"]["files_sha256"]) == {
        "manifest.json",
        "episodes.jsonl",
        "lane-receipt.json",
        "bridge/stopped.json",
    }
    fc = P.freeze_constants(**P.freeze_inputs(got, n_star=40, prefreeze_jobs=["O1", "A0a"]))
    assert fc.a1_cap_min == 111 and fc.k_base == 32 and fc.launch_a0a_min == 5.0
    for name, kwargs, message in (
        ("cut", {"statuses": {7: ["cap_truncated"]}}, "cut at the cap or never dispatched"),
        ("lost", {"statuses": {7: ["infrastructure", "infrastructure"]}}, "completed 19 of V"),
        ("long", {"seconds": 760.0}, None),
    ):
        run, bridge = a0a_run(tmp_path / name, **kwargs)
        if message is None:  # the longest episodes count: a mean slot of 769.5 s gives 24
            got = P.a0a_measurements(run, bridge, action_path_step_p95_s=2.71)
            with pytest.raises(P.PlanError, match="K_base 24 is below the floor 32"):
                P.freeze_constants(**P.freeze_inputs(got, n_star=40, prefreeze_jobs=["O1", "A0a"]))
            continue
        with pytest.raises(P.PlanError, match=message):
            P.a0a_measurements(run, bridge, action_path_step_p95_s=2.71)
    with pytest.raises(P.PlanError, match="not \\['O2'\\]"):
        P.freeze_inputs(got, n_star=40, prefreeze_jobs=["O1", "A0a", "O2"])
    assert P.freeze_inputs(got, n_star=40, prefreeze_jobs=["O1", "A0a", "A0a"])[
        "prefreeze_caps"] == [3, 25, 25]  # fmt: skip


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
    assert plan["dev_order"][:5] == P.dev_tasks(
        renderer.load_inputs(ROOT)["dev_ids"], P.dev_setup_ok(P.load_setup_check(ROOT)), 5
    )
    again = subprocess.run(
        [sys.executable, str(script), "--out", str(out)], capture_output=True, text=True
    )
    assert again.returncode != 0
    a0a, bridge = a0a_run(tmp_path / "a0a", first=10_240.0)
    frozen = tmp_path / "frozen.json"
    run = subprocess.run(
        [sys.executable, str(script), "--a0a-run-dir", str(a0a), "--a0a-bridge-dir", str(bridge),
         "--n-star", "40", "--action-path-step-p95", "2.71", "--out", str(frozen)],
        capture_output=True, text=True,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    plan = json.loads(frozen.read_text())
    assert plan["constants"]["k_base"] == 32 and len(plan["base"]) == 32
    assert plan["constants"]["launch_a0a_min"] == 4.0 and plan["constants"]["a1_cap_min"] == 111
    assert plan["a0a_measurements"]["measured"]["files_sha256"]["episodes.jsonl"]
    assert plan["anchor_tasks"] == [] and [j["job"] for j in plan["jobs"]][1:] == P.a1_job_order()
    assert all(t in plan["anchor_order"] for t in plan["flagged_tasks"])


def test_a0a_gates_read_the_step_logs():
    """Section 6.2: per harness, model turns at the cap without a complete tool call over all
    its turns; the action path's step p95 over every DesktopEnv.step."""
    from harness.q2.action_path.acceptance import quantile

    osw = [turn(False, True, 2.0, 2.5)] * 4 + [turn(True, True, 3.0)]  # a cap hit with a call
    ga = [turn(False, True, 1.0)] * 4 + [turn(True, False)]  # one in five without a call
    gates = P.a0a_gates([{"harness": "H-OSW-fixed", "steps": osw},
                         {"harness": "H-GA", "steps": ga}], 2.71)  # fmt: skip
    assert gates["truncation_share"] == {"H-OSW-fixed": 0.0, "H-GA": 0.2}
    times = [2.0, 2.5] * 4 + [3.0] + [1.0] * 4
    assert gates["step_p95_s"] == quantile(times, 0.95) == P.quantile(times, 0.95) == 3.0
    assert gates["problems"] == [] and gates["step_p95_limit_s"] == pytest.approx(5.42)
    worse = P.a0a_gates([{"harness": "H-OSW-fixed", "steps": osw},
                         {"harness": "H-GA", "steps": ga + [turn(True, False)]}], 1.4)  # fmt: skip
    assert any("truncation gate" in p and "H-GA" in p for p in worse["problems"])
    assert any("concurrency gate" in p for p in worse["problems"])  # 3.0 s > 2 x 1.4 s
    one = P.a0a_gates([{"harness": "H-GA", "steps": ga}], 2.71)
    assert one["problems"] == ["truncation gate: no H-OSW-fixed turn in A0a"]
    for values in ([], [1.0], list(range(1, 21)), [5.0, 1.0, 3.0]):
        assert P.quantile(values, 0.95) == quantile(values, 0.95)


def test_freeze_constants_enforce_a0a_gates():
    common = dict(n_star=40, a0a_slot_seconds=[640.0] * 20, launch_a0a_min=4,
                  prefreeze_caps=[3, 25], anchor_available=False)  # fmt: skip
    fc = P.freeze_constants(a0a_gates=GATES, **common)
    assert fc.truncation_share == {"H-OSW-fixed": 0.0, "H-GA": 0.0}
    assert fc.a0a_step_p95_s == 2.0 and fc.action_path_step_p95_s == 2.71
    truncated = dict(GATES, truncation_share={"H-OSW-fixed": 0.0, "H-GA": 0.25})
    with pytest.raises(P.PlanError, match="truncation gate"):
        P.freeze_constants(a0a_gates=truncated, **common)
    slow = dict(GATES, step_p95_s=5.5)  # above 2 x 2.71 s
    with pytest.raises(P.PlanError, match="concurrency gate"):
        P.freeze_constants(a0a_gates=slow, **common)
    with pytest.raises(TypeError):
        P.freeze_constants(**common)  # the gates are a required input


def test_a0a_gates_from_a_lane_run_directory(tmp_path):
    run = tmp_path / "run"
    rows = {"A0a:a0a.1:000": ("H-GA", "scored"), "A0a:a0a.1:001": ("H-OSW-fixed", "scored"),
            "A0a:a0a.2:000": ("H-GA", "infrastructure")}  # fmt: skip
    run.mkdir()
    with (run / "episodes.jsonl").open("w") as handle:
        for slot, (harness, status) in rows.items():
            handle.write(json.dumps({"slot": slot, "attempt": 1, "harness": harness,
                                     "status": status}) + "\n")  # fmt: skip
            out = run / "episodes" / f"{slot.replace(':', '_')}.a1"
            out.mkdir(parents=True)
            (out / "steps.jsonl").write_text(json.dumps(turn(False, True, 2.0)) + "\n")
    episodes = P.load_a0a_episodes(run)
    assert sorted(e["harness"] for e in episodes) == ["H-GA", "H-OSW-fixed"]  # scored only
    run, bridge = a0a_run(tmp_path / "cli")
    script = [sys.executable, "-m", "harness.q2_stage1.plan", "a0a-measurements", "--run-dir",
              str(run), "--bridge-dir", str(bridge), "--action-path-step-p95", "2.71"]  # fmt: skip
    done = subprocess.run(script, capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["a0a_gates"]["steps_timed"] == 100


# --------------------------------------------------------------------------- offline setup
# Section 5.4's offline-setup exclusion, registered before G0 item 5's second pass ran.

ARGV = {
    "26150609": ["pip", "install", "pygame"],
    "e2b5e914": ["code", "--install-extension", "ms-python.python"],
    "53ad5833": ["/bin/bash", "-c", "cd /home/user/Downloads && unzip -q vscodeEvalExtension.zip "
                 "&& code --install-extension vscodeEvalExtension/eval-0.0.1.vsix && rm -rf x"],
    "d38192b0": ["pip", "install", "/home/user/cssselect-1.3.0-py3-none-any.whl"],
}  # fmt: skip


def test_install_targets_tell_network_installs_from_local_ones():
    assert P.install_targets(ARGV["26150609"]) == [("pip", "pygame", True)]
    assert P.install_targets(ARGV["e2b5e914"]) == [("code", "ms-python.python", True)]
    assert P.install_targets(ARGV["53ad5833"]) == [
        ("code", "vscodeEvalExtension/eval-0.0.1.vsix", False)]  # fmt: skip
    assert P.install_targets(ARGV["d38192b0"]) == [
        ("pip", "/home/user/cssselect-1.3.0-py3-none-any.whl", False)]  # fmt: skip
    assert P.install_targets("sudo apt-get install -y curl") == [("apt-get", "curl", True)]
    assert P.install_targets(["python3", "-m", "pip", "install", "x"]) == [("pip", "x", True)]
    for argv in (["mkdir", "-p", "/x"], ["tar", "-xzv", "-f", "a.tar.gz"], "pkill vlc", None):
        assert P.install_targets(argv) == []


def setup_row(task: str, *, status="setup_ok", setup_steps=(), probe_steps=(), probe_replies=(),
              failures=(), diagnostics=None, attempt=1, probe=True) -> dict:  # fmt: skip
    row = {"task_id": task, "attempt": attempt, "status": status,
           "setup": {"config_steps": list(setup_steps), "failures": list(failures)}}  # fmt: skip
    if probe:
        row["postconfig_probe"] = {"config_steps": list(probe_steps),
                                   "replies": list(probe_replies)}  # fmt: skip
    if diagnostics is not None:
        row["diagnostics"] = diagnostics
    return row


def test_offline_exclusion_rules():
    step = lambda i, argv: {"step": i, "type": "command", "argv": argv}  # noqa: E731
    rows = [
        setup_row("clean", setup_steps=[step(1, ["mkdir", "-p", "/x"])]),
        setup_row("net", setup_steps=[step(2, ARGV["26150609"])]),
        setup_row("market", setup_steps=[step(1, ARGV["e2b5e914"])],
                  diagnostics=[{"argv": ["code"], "expect": "ms-python", "found": False}]),
        setup_row("vsix", setup_steps=[step(2, ARGV["53ad5833"])],
                  diagnostics=[{"argv": ["code"], "expect": "eval", "found": True}]),
        setup_row("vsix-missing", setup_steps=[step(2, ARGV["53ad5833"])],
                  diagnostics=[{"argv": ["code"], "expect": "eval", "found": False}]),
        setup_row("wheel-ok", probe_steps=[step(2, ARGV["d38192b0"])],
                  probe_replies=[{"step": 2, "status": 200, "returncode": 0}]),
        setup_row("wheel-bad", probe_steps=[step(2, ARGV["d38192b0"])],
                  probe_replies=[{"step": 2, "status": 200, "returncode": 1}]),
        setup_row("agent-state", probe_steps=[step(1, ["ls", "-R", "/home/user/x"])],
                  probe_replies=[{"step": 1, "status": 200, "returncode": 2}]),
        setup_row("failed", status="setup_failed", failures=["setup step 1 (execute): rc=1"]),
        setup_row("flaky", status="setup_failed"),
        setup_row("flaky", attempt=2),
        setup_row("unprobed", probe=False),
    ]  # fmt: skip
    tasks = sorted({r["task_id"] for r in rows} | {"absent"})
    out = P.offline_exclusions(rows, tasks)
    assert sorted(out) == ["absent", "failed", "market", "net", "unprobed", "vsix-missing",
                           "wheel-bad"]  # fmt: skip
    assert out["net"] == ["(a) setup step 2: pip install pygame"]
    assert out["market"][0].startswith("(a)") and out["market"][1].startswith("(b) diagnostic")
    assert out["wheel-bad"][0].startswith("(c) postconfig step 2 install failed")
    assert out["absent"] == ["(b) no setup-check-v2 record"]
    pool = P.eligible_pool(["0a0faba3-x", "b", "c"], {"c": ["(a)"]})
    assert pool == ["b"]


def test_offline_excluded_is_the_registered_rule_on_the_committed_records(inputs):
    """``plan.OFFLINE_EXCLUDED`` is section 5.4's rule applied to G0 item 5's second-pass
    records (by their registered SHA-256), over every pool and dev task; the draw runs on
    the eligible pool and keeps the 32-task floor."""
    rows = P.load_setup_check(ROOT)
    tasks = P.task_pool(inputs["confirm_ids"]) + sorted(inputs["dev_ids"])
    computed = P.offline_exclusions(rows, tasks)
    assert {t: tuple(r) for t, r in computed.items()} == P.OFFLINE_EXCLUDED
    assert {r["task_id"] for r in rows} == set(tasks)  # every pool and dev task was checked
    pool = P.eligible_pool(inputs["confirm_ids"], P.OFFLINE_EXCLUDED)
    draw = P.draw_tasks(pool, inputs["domain"], 32)
    assert len(draw["base"]) == 32 and not set(draw["base"]) & set(P.OFFLINE_EXCLUDED)
    dev = P.dev_tasks(inputs["dev_ids"], P.dev_setup_ok(rows), 5)
    assert not set(dev) & set(P.OFFLINE_EXCLUDED)
