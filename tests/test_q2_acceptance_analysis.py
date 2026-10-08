"""The acceptance analysis (harness/q2/action_path/acceptance.py) on synthetic campaigns."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from harness.q2.action_path import acceptance as acc
from harness.q2.action_path import order, volume
from harness.q2.vm.manifest import ladder_reps

ROOT = Path(__file__).resolve().parents[1]
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())


def campaign(
    plan: list[dict],
    job: str = "900",
    concurrency: int = 1,
    fail: frozenset = frozenset(),
    session_range: list[int] | None = None,
    boot_s: float = 18.0,
    step_s: float = 1.5,
) -> dict:
    """A campaign whose every trial passes except the (setting, cell) pairs in ``fail``."""
    sessions = []
    for index, session in enumerate(plan):
        trials = []
        for seq, cell in session["trials"]:
            trials.append(
                {
                    "seq": seq,
                    "cell": cell,
                    "setting": session["setting"],
                    "pass": (session["setting"], cell) not in fail and cell not in fail,
                    "infra": [],
                    "retried": [],
                    "c4": None,
                    "events": [["KeyPress", 38, 16, 97]],
                    "text": "a",
                    "terminal": None,
                    "steps_s": [step_s],
                }
            )
        sessions.append(
            {
                "cycle": index,
                "setting": session["setting"],
                "boot_s": boot_s,
                "error": None,
                "trials": trials,
                "snapshots": [
                    {"t": index * 2.0, "squeue_foreign": []},
                    {"t": index * 2.0 + 1, "squeue_foreign": []},
                ],
            }
        )
    return {
        "job": job,
        "manifest": {
            "git_sha": "a" * 40,
            "vm": {"concurrency": concurrency},
            "workload": {"session_range": session_range},
        },
        "receipt": {
            "summary": {"infra_gates_pass": True, "leaked_volumes": []},
            "qcow2_unchanged": True,
            "labelled_containers_left": [],
        },
        "slurm": {"state": "COMPLETED", "exit_code": "0:0"},
        "batch": {"driver_exit": 0, "labelled_containers_left": 0},
        "sessions": sessions,
        "earlier": [],
    }


def ids(layer: str) -> list[str]:
    return [c["id"] for c in CELLS["layers"][layer]]


def a1_plan(seed: int) -> list[dict]:
    return order.plan(ids("L0-fixed"), seed, 5, list(order.SETTINGS), acceptance=True)


def test_a1_passes_only_with_every_gating_trial_and_the_whole_order():
    good = {seed: [campaign(a1_plan(seed), job=str(seed))] for seed in (43, 44)}
    assert acc.a1(good)["pass"]
    # A non-gating entry may fail; it is reported, not gating.
    soft = copy.deepcopy(good)
    soft[43] = [campaign(a1_plan(43), fail=frozenset({"click_button_back"}))]
    assert acc.a1(soft)["pass"]
    assert acc.a1(soft)["entries"][43]["click_button_back"] == "FAIL"
    # A gating entry failing in one setting only is a failure (section 5).
    hard = copy.deepcopy(good)
    hard[44] = [campaign(a1_plan(44), fail=frozenset({("screenshot+a11y", "key_enter")}))]
    result = acc.a1(hard)
    assert not result["pass"] and result["entries"][44]["key_enter"] == "FLAKY"
    # A campaign cut short, or one whose job did not complete, cannot pass.
    short = copy.deepcopy(good)
    short[43][0]["sessions"].pop()
    assert not acc.a1(short)["pass"]
    failed_job = copy.deepcopy(good)
    failed_job[44][0]["slurm"] = {"state": "TIMEOUT", "exit_code": "0:15"}
    assert not acc.a1(failed_job)["pass"]
    assert not acc.a1({43: good[43]})["pass"]


def test_a2_ignores_outside_spec_cells_and_gates_declared_ones():
    def plan(layer):
        return order.plan(ids(layer), 43, 5, list(order.SETTINGS), acceptance=True)

    good = {layer: [campaign(plan(layer))] for layer in ("H-OSW-fixed", "H-GA")}
    assert acc.a2(good)["pass"]
    outside = dict(good, **{"H-GA": [campaign(plan("H-GA"), fail=frozenset({"R02"}))]})
    assert acc.a2(outside)["pass"]
    declared = dict(good, **{"H-OSW-fixed": [campaign(plan("H-OSW-fixed"), fail={"R08"})]})
    assert not acc.a2(declared)["pass"]


def test_c1_needs_five_failures_of_five_on_each_known_defect():
    def plan(layer):
        return order.plan(ids(layer), 42, 5, ["screenshot"])

    defects = {layer: frozenset(cells) for layer, cells in acc.C1_MUST_FAIL.items()}
    good = {layer: [campaign(plan(layer), fail=defects[layer])] for layer in acc.C1_MUST_FAIL}
    assert acc.c1(good)["pass"]
    partial = copy.deepcopy(good)
    trials = [
        t for s in partial["H-GA-buggy"][0]["sessions"] for t in s["trials"] if t["cell"] == "R01"
    ]
    trials[0]["pass"] = True  # 1 of 5 passed: a defect in the control itself
    assert not acc.c1(partial)["pass"]


def _c2_plan():
    """v2's C2 order: the 100 entries in the seed-45 shuffle (decision D40)."""
    return order.plan(ids("L0-fixed"), acc.C2_SEED, 5, ["screenshot"], criterion="C2")


def test_c2_requires_the_exact_predicted_failing_set():
    import yaml

    predicted = frozenset(yaml.safe_load(acc.PREDICTION.read_text())["predicted_fail"])
    # v2's prediction (decisions D40 and D43): v1's failing set; chord_super_d passes.
    assert "chord_super_d" not in predicted and len(predicted) == 8
    plan = _c2_plan()
    assert acc.c2([campaign(plan, fail=predicted)])["pass"]
    assert not acc.c2([campaign(plan, fail=predicted | {"key_enter"})])["pass"]
    assert not acc.c2([campaign(plan, fail=predicted - {"type_emoji"})])["pass"]
    # chord_super_d failing, as in v1's C2 under v1's judge, fails v2's C2.
    assert not acc.c2([campaign(plan, fail=predicted | {"chord_super_d"})])["pass"]


def test_c2_runs_v2s_own_order_seed():
    """Decision D40: a C2 campaign that ran v1's seed-42 order is not v2's C2."""
    import yaml

    assert acc.C2_SEED == 45
    predicted = frozenset(yaml.safe_load(acc.PREDICTION.read_text())["predicted_fail"])
    v1_order = order.plan(ids("L0-fixed"), 42, 5, ["screenshot"])
    result = acc.c2([campaign(v1_order, fail=predicted)])
    assert not result["pass"]
    assert any("C2" in problem for problem in result["problems"]), result["problems"]


def test_c3_kills_equivalence_and_survivors():
    import yaml

    from harness.q2.action_path import mutants as kit

    operators = yaml.safe_load(
        (ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text()
    )
    pairs = kit.scored_pairs(operators)
    plans = {layer: order.plan(ids(layer), 42, 1, ["screenshot"]) for layer in acc.C3_LAYERS}
    references = {layer: [campaign(plans[layer])] for layer in acc.C3_LAYERS}
    runs = {(op, layer): [campaign(plans[layer], fail={"R14", "key_enter"})] for op, layer in pairs}
    assert acc.c3(runs, references)["pass"]
    # An outside-spec cell cannot kill (R09 is outside both harnesses' specs).
    op = next(p for p in pairs if p[1] == "H-GA")
    runs_outside = dict(runs)
    runs_outside[op] = [campaign(plans["H-GA"], fail={"R09"})]
    for session in runs_outside[op][0]["sessions"]:
        for trial in session["trials"]:
            if trial["cell"] == "R09":
                trial["events"] = []  # the mutant changed R09's stream, and only R09's
    result = acc.c3(runs_outside, references)
    assert not result["pass"] and result["mutants"][f"{op[0]} H-GA"]["outcome"] == "survived"
    # A mutant identical to the reference on every cell is equivalent, not a survivor.
    runs_equal = dict(runs)
    runs_equal[op] = [campaign(plans["H-GA"])]
    result = acc.c3(runs_equal, references)
    assert result["pass"] and result["mutants"][f"{op[0]} H-GA"]["outcome"] == "equivalent"
    changed = copy.deepcopy(runs_equal[op])
    changed[0]["sessions"][0]["trials"][0]["text"] = "b"
    runs_equal[op] = changed
    assert not acc.c3(runs_equal, references)["pass"]


def test_a4_must_tile_the_volume_plan_at_n_star():
    plan_data = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())
    realized = volume.sessions(plan_data, 43)
    full = [
        {"setting": s, "trials": list(enumerate(chunk))}
        for s in order.SETTINGS
        for chunk in realized[s]
    ]
    halves = [
        campaign(full[:500], job="1", concurrency=8, session_range=[0, 500]),
        campaign(full[500:], job="2", concurrency=8, session_range=[500, len(full)]),
    ]
    assert acc.a4(halves, 8)["pass"]
    assert not acc.a4(halves, 16)["pass"]
    assert not acc.a4(halves[:1], 8)["pass"]
    halves[1]["sessions"][3]["trials"][0]["pass"] = False
    assert acc.a4(halves, 8)["failures"] == 1 and not acc.a4(halves, 8)["pass"]


def _a4_halves() -> list[dict]:
    plan_data = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())
    realized = volume.sessions(plan_data, 43)
    full = [
        {"setting": s, "trials": list(enumerate(chunk))}
        for s in order.SETTINGS
        for chunk in realized[s]
    ]
    return [
        campaign(full[:500], job="1", concurrency=8, session_range=[0, 500]),
        campaign(full[500:], job="2", concurrency=8, session_range=[500, len(full)]),
    ]


def _hit(trial: dict, *reasons: str) -> None:
    """A trial a guest-server restart hit, failing for ``reasons`` (``infra: <type>`` ones)."""
    trial["pass"] = False
    trial["reasons"] = list(reasons)
    trial["infra"] = sorted(r[len("infra: ") :] for r in reasons if r.startswith("infra: "))


def test_a4_does_not_count_a_trial_whose_only_failure_is_a_restart():
    """Decision D30: the restart (and the tree it left undelivered) is reported, not counted."""
    halves = _a4_halves()
    halves[1]["sessions"][60]["restarts"] = 1
    halves[1]["sessions"][60]["accessibility_calls"] = 68
    trial = halves[1]["sessions"][60]["trials"][7]
    _hit(trial, "infra: guest_server_restart")
    result = acc.a4(halves, 8)
    assert result["pass"] and result["failures"] == 0 and result["restart_only_trials"] == 1
    report = result["guest_server"]
    assert report["restarts"] == 1 and report["accessibility_calls"] == 68
    assert (
        report["trials_hit"][0]["cell"] == trial["cell"] and not report["trials_hit"][0]["counted"]
    )
    rate = report["development_rate"]
    assert rate["restarts"] == 1 and rate["accessibility_calls"] == 8114
    assert rate["interval_95"][0] < rate["rate"] < rate["interval_95"][1]
    _hit(trial, "infra: accessibility", "infra: guest_server_restart")
    assert acc.a4(halves, 8)["pass"]


@pytest.mark.parametrize(
    "reasons",
    [
        ("infra: guest_server_restart", "infra: probe_absent"),
        ("infra: guest_server_restart", "infra: execute"),
        ("infra: guest_server_restart", "text 'a' != 'b'"),
        ("infra: guest_server_restart", "marker [3, 1] != probe final [3, 2]"),
        ("infra: accessibility",),
    ],
)
def test_a4_still_counts_every_other_failure_of_a_trial_a_restart_hit(reasons):
    halves = _a4_halves()
    _hit(halves[0]["sessions"][3]["trials"][0], *reasons)
    result = acc.a4(halves, 8)
    assert not result["pass"] and result["failures"] == 1


def test_a4_excuses_restart_only_trials_of_an_earlier_attempt_too():
    halves = _a4_halves()
    earlier = copy.deepcopy(halves[0])
    earlier["job"], earlier["batch"], earlier["slurm"] = "0", None, None
    earlier["sessions"] = earlier["sessions"][:4]
    _hit(earlier["sessions"][1]["trials"][2], "infra: guest_server_restart")
    halves[0]["earlier"] = [earlier]
    assert acc.a4(halves, 8)["pass"]
    _hit(earlier["sessions"][1]["trials"][2], "infra: guest_server_restart", "infra: execute")
    assert not acc.a4(halves, 8)["pass"]


def _plan_calls(plan: list[dict]) -> list[int]:
    """Each session's accessibility calls as a complete record shows them: the reset
    observation and one per executed action."""
    l0 = {c["id"]: c for c in CELLS["layers"]["L0-fixed"]}

    def steps(cell: str) -> int:
        actions = [a["op"] for a in l0[cell]["actions"]]
        return actions.index("terminate") if "terminate" in actions else len(actions)

    return [1 + sum(steps(cell) for _, cell in s["trials"]) for s in plan]


A7_SESSION_CALLS = _plan_calls(acc.observation_plan())


def _a7(restarts_per_session: dict[int, int], calls: int | None = None, **kwargs) -> list[dict]:
    """A7's campaign; each session shows the plan's calls, or ``calls`` when given."""
    plan = acc.observation_plan()
    run = campaign(plan, job="7", concurrency=kwargs.pop("concurrency", 8), **kwargs)
    for index, session in enumerate(run["sessions"]):
        session["accessibility_calls"] = A7_SESSION_CALLS[index] if calls is None else calls
        session["restarts"] = restarts_per_session.get(index, 0)
    return [run]


def test_poisson_bounds_are_the_exact_ones():
    assert acc.poisson_upper(0) == pytest.approx(2.99573, abs=1e-4)
    assert acc.poisson_upper(1) == pytest.approx(4.74386, abs=1e-4)
    assert acc.poisson_upper(12) == pytest.approx(19.4426, abs=1e-3)
    assert acc.poisson_lower(1, 0.025) == pytest.approx(0.025318, abs=1e-5)
    assert acc.poisson_upper(1, 0.025) == pytest.approx(5.5716, abs=1e-3)


def test_a7_runs_the_gating_set_in_the_accessibility_setting_only():
    from harness.q2.vm.manifest import OBSERVATION_REPS

    plan = acc.observation_plan()
    assert {s["setting"] for s in plan} == {"screenshot+a11y"}
    cells = [cell for s in plan for _, cell in s["trials"]]
    gating = set(
        json.loads((ROOT / "harness/q2/action_path/gating_set.json").read_text())["gating"]
    )
    assert set(cells) == gating and len(cells) == len(gating) * OBSERVATION_REPS
    assert len(plan) == 516 and len(cells) == 30960


def test_a7_judges_the_upper_95_bound_on_restarts_per_call():
    # The plan's 39,036 calls; 12 restarts give 19.44 / 39,036 = 4.98e-4 (section 9).
    assert sum(A7_SESSION_CALLS) == 39036
    twelve = _a7({i: 1 for i in range(12)})
    result = acc.a7(twelve, 8)
    assert result["pass"] and result["restarts"] == 12 and result["accessibility_calls"] == 39036
    assert result["upper_95"] == pytest.approx(19.4426 / 39036, rel=1e-4)
    assert result["upper_95"] <= 5e-4
    per_session = result["per_session"]
    assert per_session["sessions"] == 516 and per_session["sessions_with_restart"] == 12
    assert per_session["upper_95"] == pytest.approx(19.4426 / 516, rel=1e-4)
    thirteen = _a7({i: 1 for i in range(13)})
    assert not acc.a7(thirteen, 8)["pass"]
    assert acc.a7(_a7({}), 8)["upper_95"] == pytest.approx(2.9957 / 39036, rel=1e-4)
    # Trial failures are reported, not judged; the plan, N* and the end state are.
    failing = _a7({}, fail=frozenset({"key_enter"}))
    result = acc.a7(failing, 8)
    assert result["pass"] and result["failed_trials"] > 0
    assert not acc.a7(_a7({}), 16)["pass"]
    short = _a7({})
    short[0]["sessions"].pop()
    assert not acc.a7(short, 8)["pass"]
    killed = _a7({})
    killed[0]["batch"] = None
    assert not acc.a7(killed, 8)["pass"]
    assert not acc.a7(_a7({}, calls=0), 8)["pass"]


def test_a7_keeps_the_restarts_of_an_attempt_that_did_not_count():
    rerun = _a7({i: 1 for i in range(12)})
    earlier = copy.deepcopy(rerun[0])
    earlier["job"], earlier["batch"], earlier["slurm"] = "6", None, None
    earlier["sessions"] = earlier["sessions"][:3]
    for session in earlier["sessions"]:
        session["restarts"] = 1
    rerun[0]["earlier"] = [earlier]
    result = acc.a7(rerun, 8)
    # k over every attempt; n over the counting attempt only (the earlier one's calls are
    # reported, never added to the denominator).
    assert result["restarts"] == 15 and result["accessibility_calls"] == 39036
    assert result["accessibility_calls_every_attempt"] == 39036 + sum(A7_SESSION_CALLS[:3])
    assert result["per_session"]["sessions"] == 516
    assert result["per_session"]["sessions_with_restart"] == 15
    assert not result["pass"]


def test_a7_cancelling_a_failing_run_and_rerunning_it_cannot_help():
    """Optional continuation (design decision 37): an operator who cancels a run once its
    13th restart arrives and reruns the plan must not gain from it. Pooling the calls of
    both attempts would pass this record (19 restarts in about 73,800 calls: bound
    3.8e-4); the registered rule judges 19 restarts against the counting attempt's 39,036
    calls."""
    rerun = _a7({i: 1 for i in range(6)})
    assert acc.a7(rerun, 8)["pass"]
    cancelled = copy.deepcopy(rerun[0])
    cancelled["job"], cancelled["batch"] = "6", None
    cancelled["slurm"] = {"state": "CANCELLED", "exit_code": "0:15"}
    cancelled["sessions"] = cancelled["sessions"][:460]
    for index, session in enumerate(cancelled["sessions"]):
        session["restarts"] = 1 if index < 13 else 0
    rerun[0]["earlier"] = [cancelled]
    pooled = acc.poisson_upper(19) / (39036 + sum(A7_SESSION_CALLS[:460]))
    assert pooled < acc.OBSERVATION_BOUND  # what pooling would have allowed
    result = acc.a7(rerun, 8)
    assert result["restarts"] == 19 and result["accessibility_calls"] == 39036
    assert result["upper_95"] == pytest.approx(acc.poisson_upper(19) / 39036)
    assert not result["pass"]
    # Without a restart in the cancelled attempt, the rerun stands as it would alone.
    for session in cancelled["sessions"]:
        session["restarts"] = 0
    assert acc.a7(rerun, 8)["pass"] and acc.a7(rerun, 8)["restarts"] == 6


def test_a7_caps_its_calls_at_the_plan():
    """Decision D33: n is the counting attempt's calls capped at the plan's 39,036, so a
    record showing more calls than the plan makes cannot lower the bound."""
    assert acc.OBSERVATION_PLAN_CALLS == acc.observation_plan_calls() == 39036
    # 13 restarts fail at the plan's calls (20.67 / 39,036 = 5.3e-4) and would pass at the
    # 41,796 calls of 516 sessions x 81 (4.95e-4).
    inflated = _a7({i: 1 for i in range(13)}, calls=81)
    assert acc.poisson_upper(13) / (516 * 81) <= acc.OBSERVATION_BOUND
    result = acc.a7(inflated, 8)
    assert not result["pass"]
    assert result["accessibility_calls"] == 39036 and result["plan_calls"] == 39036
    assert result["accessibility_calls_counting"] == 516 * 81
    assert result["upper_95"] == pytest.approx(acc.poisson_upper(13) / 39036)
    # Fewer calls than the plan (an observation that never reached the server) stand as
    # recorded.
    short = acc.a7(_a7({}, calls=70), 8)
    assert short["accessibility_calls"] == 516 * 70 and short["pass"]


def test_a7_runs_under_attempt_one_only():
    """Section 11: A7 has no repair attempt; the analysis refuses one as manifest.py does."""
    repaired = _a7({})
    repaired[0]["manifest"]["workload"]["attempt"] = 2
    result = acc.a7(repaired, 8)
    assert not result["pass"] and any("attempt 1" in p for p in result["problems"])
    first = _a7({})
    first[0]["manifest"]["workload"]["attempt"] = 1
    assert acc.a7(first, 8)["pass"]


def test_foreign_load_aborts_a_rung():
    plan = order.plan(ids("L0-fixed"), 43, ladder_reps(8), list(order.SETTINGS), acceptance=True)
    rung = campaign(plan, job="77", concurrency=8)
    assert acc.foreign_abort(rung) == []
    started = copy.deepcopy(rung)
    started["sessions"][2]["snapshots"][1]["squeue_foreign"] = [
        ["78", "u", "RUNNING", "4", "", "x"]
    ]
    assert any("started" in r for r in acc.foreign_abort(started))
    heavy = copy.deepcopy(rung)
    for session in heavy["sessions"]:
        for snapshot in session["snapshots"]:
            snapshot["squeue_foreign"] = [["50", "u", "RUNNING", "16", "gres:gpu:1", "y"]]
    assert acc.foreign_abort(heavy) == ["foreign jobs hold 16 CPUs"]
    # Our own job and pending jobs are not foreign load.
    own = copy.deepcopy(rung)
    own["sessions"][0]["snapshots"][0]["squeue_foreign"] = [
        ["77", "u", "RUNNING", "33", "", "q2"],
        ["79", "u", "PENDING", "64", "", "z"],
    ]
    assert acc.foreign_abort(own) == []


def test_n_star_is_the_largest_qualifying_rung():
    a1 = [campaign(a1_plan(43), step_s=1.5), campaign(a1_plan(44), step_s=1.5)]

    def rung(n, **kwargs):
        plan = order.plan(
            ids("L0-fixed"), 43, ladder_reps(n), list(order.SETTINGS), acceptance=True
        )
        return [campaign(plan, job=str(n), concurrency=n, **kwargs)]

    rungs = {8: rung(8), 16: rung(16), 24: rung(24, step_s=3.5), 32: rung(32, boot_s=200.0)}
    result = acc.n_star(a1, rungs)
    assert result["n_star"] == 16 and result["program_kill_criterion"]
    assert not result["rungs"][24]["qualifies"] and "step p95" in result["rungs"][24]["problems"][0]
    assert "boot p95" in result["rungs"][32]["problems"][0]
    assert acc.n_star(a1, {})["n_star"] == 1
    gated = {8: rung(8, fail=frozenset({"key_enter"}))}
    assert acc.n_star(a1, gated)["n_star"] == 1


def test_c4_counts_only_entries_with_a_reference():
    a1 = [campaign(a1_plan(43))]
    trials = [t for s in a1[0]["sessions"] for t in s["trials"]]
    trials[0]["c4"], trials[1]["c4"] = True, True
    assert acc.c4(a1) == {"pass": True, "problems": [], "trials_checked": 2}
    trials[1]["c4"] = False
    assert not acc.c4(a1)["pass"]


@pytest.mark.parametrize("field", ["qcow2_unchanged", "labelled_containers_left"])
def test_a5_needs_clean_receipts_and_twenty_pristine_resets(field):
    reset = campaign([], job="5")
    reset["receipt"]["summary"].update(sentinel_reset_checks=20, sentinel_pristine=20)
    other = campaign([], job="6")
    assert acc.a5(reset, [other], "a" * 40)["pass"]
    assert not acc.a5(reset, [other], "b" * 40)["pass"]
    dirty = copy.deepcopy(other)
    dirty["receipt"][field] = False if field == "qcow2_unchanged" else ["c"]
    assert not acc.a5(reset, [dirty], "a" * 40)["pass"]
    short = copy.deepcopy(reset)
    short["receipt"]["summary"].update(sentinel_reset_checks=19, sentinel_pristine=19)
    assert not acc.a5(short, [other], "a" * 40)["pass"]


def _driver_campaign(criterion, layer, seed, reps, settings, cells="all", mutant=None):
    """A campaign whose trials are exactly what the driver would run for this manifest."""
    from harness.q2.vm import driver

    manifest = {
        "randomness": {"seeds": [seed]},
        "workload": {
            "kind": "suite-acceptance",
            "criterion": criterion,
            "layer": layer,
            "reps": reps,
            "settings": settings,
            "cells": cells,
            "session_trials": 60,
            "session_range": None,
            "mutant": mutant,
        },
    }
    volume_plan = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())
    return campaign(driver.acceptance_plan(manifest, CELLS, volume_plan), job=f"{criterion}{seed}")


def test_the_analysis_expects_the_order_the_driver_runs():
    from harness.q2.vm import driver
    from harness.q2.vm.manifest import CANARY_APPS

    both = list(order.SETTINGS)
    a1 = {s: [_driver_campaign("A1", "L0-fixed", s, 5, both)] for s in (43, 44)}
    assert acc.a1(a1)["pass"]
    a2 = {h: [_driver_campaign("A2", h, 43, 5, both)] for h in ("H-OSW-fixed", "H-GA")}
    assert acc.a2(a2)["pass"]
    a3 = {
        layer: [_driver_campaign("A3", layer, 43, 30, both, cells="stress")]
        for layer in acc.C3_LAYERS
    }
    assert acc.a3(a3)["pass"]
    from harness.q2.vm.manifest import OBSERVATION_REPS

    a7 = _driver_campaign("A7", "L0-fixed", 43, OBSERVATION_REPS, ["screenshot+a11y"], "gating")
    for session in a7["sessions"]:
        session["accessibility_calls"] = 76
    assert acc.a7([a7], 1)["pass"]
    c1 = {
        layer: [_driver_campaign("C1", layer, 42, 5, ["screenshot"])] for layer in acc.C1_MUST_FAIL
    }
    for layer, cells in acc.C1_MUST_FAIL.items():
        for session in c1[layer][0]["sessions"]:
            for trial in session["trials"]:
                trial["pass"] = trial["cell"] not in cells
    assert acc.c1(c1)["pass"]
    canary = {
        "randomness": {"seeds": [43]},
        "workload": {
            "kind": "canary-acceptance",
            "apps": list(CANARY_APPS),
            "reps": 5,
            "session_trials": 60,
        },
    }
    assert acc.a6([campaign(driver.session_plan(canary, CELLS))])["pass"]


# --- fix pass after the 2026-10-07 review of 2b492cd ---------------------------------------------

STATE = {"Shift": 1, "Control": 4, "Mod1": 8, "Mod4": 64}


def _key_records(expect_events, release_state: bool, raw_only: bool) -> list[list]:
    """Observed records for an R-dev cell; releases optionally lose their modifier state."""
    from harness.q2.action_path.ir import KEYSYM_VALUES

    out = []
    for index, (kind, name, states) in enumerate(expect_events):
        state = sum(STATE[s] for s in states)
        if kind == "KeyRelease" and not release_state:
            state = 0
        keysym = KEYSYM_VALUES[name]
        if raw_only:  # tap window, timestamp dropped: [kind, keycode, state, keysym0]
            out.append([kind, 40 + index, state, keysym])
        else:  # probe log: [kind, keycode, state, x, y, time, keysym0]
            out.append([kind, 40 + index, state, 0, 0, 1000 + index, keysym])
    return out


def _c2_campaign(plan, mutate):
    """A C2 campaign failing exactly the predicted set, then ``mutate(trial)`` on every trial."""
    import yaml

    predicted = frozenset(yaml.safe_load(acc.PREDICTION.read_text())["predicted_fail"])
    run = campaign(plan, fail=predicted)
    for session in run["sessions"]:
        for trial in session["trials"]:
            trial["reasons"] = [] if trial["pass"] else ["text 'a' != 'b'"]
            mutate(trial)
    return run


def test_c2_judges_l0_raw_on_the_event_and_text_channels_only():
    """Design decision 34: marker and release-state timing never decide C2."""
    plan = _c2_plan()
    l0 = {c["id"]: c for c in CELLS["layers"]["L0-fixed"]}
    assert acc.c2([_c2_campaign(plan, lambda t: None)])["pass"]

    def stale_marker(trial):
        if trial["cell"] in ("type_plain", "no_action_control"):
            trial["pass"] = False
            trial["reasons"] = ["marker [3, 1] != probe final [3, 2]"]

    result = acc.c2([_c2_campaign(plan, stale_marker)])
    assert result["pass"], result["problems"]
    assert result["strict_entries"]["type_plain"] == "FAIL"
    assert result["entries"]["type_plain"] == "PASS"

    def released_without_state(trial):
        cell = l0[trial["cell"]]
        if trial["cell"] in ("chord_ctrl_alt_shift_r", "chord_ctrl_c"):
            raw_only = cell["observable"] == "raw-only"
            records = _key_records(cell["expect"]["events"], False, raw_only)
            trial["pass"] = False
            trial["reasons"] = ["R-dev projection differs: (releases lost their state)"]
            trial["events" if raw_only else "probe_events"] = records

    assert acc.c2([_c2_campaign(plan, released_without_state)])["pass"]

    def press_without_state(trial):
        cell = l0[trial["cell"]]
        if trial["cell"] == "chord_ctrl_c":
            events = [list(e) for e in cell["expect"]["events"]]
            events[1][2] = []  # the c press lost Control: a real defect, not timing
            trial["pass"] = False
            trial["reasons"] = ["R-dev projection differs: (press lost Control)"]
            trial["probe_events"] = _key_records(events, True, False)

    result = acc.c2([_c2_campaign(plan, press_without_state)])
    assert not result["pass"] and "chord_ctrl_c" in result["problems"][-1]

    first_type_plain = min(seq for s in plan for seq, cell in s["trials"] if cell == "type_plain")

    def marker_and_infra(trial):
        # One repetition of five with an infrastructure failure: FLAKY, an unpredicted miss.
        if trial["seq"] == first_type_plain:
            trial["pass"] = False
            trial["reasons"] = ["marker unreadable: x", "infra: execute"]
            trial["infra"] = ["execute"]

    result = acc.c2([_c2_campaign(plan, marker_and_infra)])
    assert not result["pass"] and result["entries"]["type_plain"] == "FLAKY"

    def text_and_marker(trial):
        if trial["cell"] == "type_spaces":
            trial["pass"] = False
            trial["reasons"] = ["text 'a' != ' a '", "marker [1, 1] != probe final [1, 2]"]

    assert not acc.c2([_c2_campaign(plan, text_and_marker)])["pass"]


def test_c3_counts_only_clean_kills_against_a_clean_reference():
    import yaml

    from harness.q2.action_path import mutants as kit

    operators = yaml.safe_load(
        (ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text()
    )
    pairs = kit.scored_pairs(operators)
    plans = {layer: order.plan(ids(layer), 42, 1, ["screenshot"]) for layer in acc.C3_LAYERS}
    references = {layer: [campaign(plans[layer])] for layer in acc.C3_LAYERS}
    runs = {(op, layer): [campaign(plans[layer], fail={"R14", "key_enter"})] for op, layer in pairs}
    op = next(p for p in pairs if p[1] == "L0-fixed")
    # A cell that fails only through an infrastructure failure never kills.
    infra_only = dict(runs)
    infra_only[op] = [campaign(plans["L0-fixed"], fail={"key_enter"})]
    for session in infra_only[op][0]["sessions"]:
        for trial in session["trials"]:
            if trial["cell"] == "key_enter":
                trial["infra"] = ["tap_window_missing"]
                trial["events"] = []
    result = acc.c3(infra_only, references)
    entry = result["mutants"][f"{op[0]} L0-fixed"]
    assert not result["pass"] and entry["outcome"] == "survived"
    assert entry["infra_cells"] == ["key_enter"] and entry["killers"] == []
    # A cell the unmutated reference also failed cannot kill.
    flaky_reference = copy.deepcopy(references)
    flaky_reference["L0-fixed"] = [campaign(plans["L0-fixed"], fail={"key_enter"})]
    lone = dict(runs)
    lone[op] = [campaign(plans["L0-fixed"], fail={"key_enter"})]
    entry = acc.c3(lone, flaky_reference)["mutants"][f"{op[0]} L0-fixed"]
    assert entry["outcome"] != "killed" and entry["reference_not_clean"] == ["key_enter"]
    # A clean kill reports the observed killers next to the predicted ones.
    entry = acc.c3(runs, references)["mutants"][f"{op[0]} L0-fixed"]
    assert entry["outcome"] == "killed" and entry["killers"] == ["key_enter"]
    assert isinstance(entry["predicted_killers"], list)
    # Without a reference run nothing can be killed.
    assert not acc.c3(runs, {})["pass"]


def test_end_state_comes_from_the_batch_record_or_slurm():
    good = campaign(a1_plan(43))
    assert acc.counting_problems(good) == []
    no_slurm = dict(good, slurm=None)
    assert acc.counting_problems(no_slurm) == []
    unknown = dict(good, slurm=None, batch=None)
    assert "end state unknown" in acc.counting_problems(unknown)[0]
    killed = dict(good, batch=None)
    assert "never recorded its end" in acc.counting_problems(killed)[0]
    timeout = dict(good, slurm={"state": "TIMEOUT", "exit_code": "0:15"})
    assert "TIMEOUT" in acc.counting_problems(timeout)[0]
    infra = dict(good, slurm=None, batch={"driver_exit": 3, "labelled_containers_left": 0})
    assert "driver_exit=3" in acc.counting_problems(infra)[0]


def test_reruns_are_capped_and_never_erase_failures():
    good = campaign(a1_plan(43))
    incomplete = copy.deepcopy(good)
    incomplete["job"], incomplete["batch"], incomplete["slurm"] = "899", None, None
    incomplete["sessions"] = incomplete["sessions"][:3]
    rerun = dict(copy.deepcopy(good), earlier=[incomplete])
    assert acc.a1({43: [rerun], 44: [campaign(a1_plan(44))]})["pass"]
    # A campaign that counted cannot be rerun.
    counted = dict(copy.deepcopy(good), earlier=[copy.deepcopy(good)])
    assert any("counted and was rerun" in p for p in acc.campaign_problems(counted))
    # A failed trial of an abandoned attempt still counts against the criterion.
    failing = copy.deepcopy(incomplete)
    failing["sessions"][0]["trials"][0]["pass"] = False
    hidden = dict(copy.deepcopy(good), earlier=[failing])
    assert any("failed trials" in p for p in acc.campaign_problems(hidden))
    assert not acc.a1({43: [hidden], 44: [campaign(a1_plan(44))]})["pass"]
    # At most two attempts.
    third = dict(copy.deepcopy(good), earlier=[incomplete, copy.deepcopy(incomplete)])
    assert any("3 attempts" in p for p in acc.campaign_problems(third))


def test_an_aborted_rung_may_be_rerun_once_and_its_failures_do_not_count():
    a1 = [campaign(a1_plan(43)), campaign(a1_plan(44))]
    plan = order.plan(ids("L0-fixed"), 43, ladder_reps(8), list(order.SETTINGS), acceptance=True)
    aborted = campaign(plan, job="80", concurrency=8, fail=frozenset({"key_enter"}))
    aborted["sessions"][1]["snapshots"][1]["squeue_foreign"] = [
        ["81", "u", "RUNNING", "2", "", "x"]
    ]
    assert acc.foreign_abort(aborted)
    rerun = dict(campaign(plan, job="82", concurrency=8), earlier=[aborted])
    result = acc.n_star(a1, {8: [rerun]})
    assert result["n_star"] == 8, result["rungs"][8]["problems"]
    assert result["rungs"][8]["earlier_attempts"][0]["failed_trials"] > 0
    # A rung that ran cleanly cannot be rerun to replace its result.
    clean = campaign(plan, job="83", concurrency=8)
    replaced = dict(campaign(plan, job="84", concurrency=8), earlier=[clean])
    assert acc.n_star(a1, {8: [replaced]})["n_star"] == 1
    # A third attempt is refused even after two aborts.
    twice = dict(campaign(plan, job="85", concurrency=8), earlier=[aborted, aborted])
    assert acc.n_star(a1, {8: [twice]})["n_star"] == 1


def test_one_criterion_runs_one_source_tree():
    first, second = campaign(a1_plan(43)[:9], job="1"), campaign(a1_plan(43)[9:], job="2")
    assert acc.a1({43: [first, second], 44: [campaign(a1_plan(44))]})["pass"]
    second["manifest"]["git_sha"] = "c" * 40
    result = acc.a1({43: [first, second], 44: [campaign(a1_plan(44))]})
    assert not result["pass"] and "different source trees" in result["problems"][0]


def _write_run(tmp_path, cycle: dict, preflight: str) -> str:
    run = tmp_path / "run"
    (run / "cycles").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"vm": {"concurrency": 1}}))
    (run / "receipt.json").write_text(json.dumps({"job_id": "700"}))
    (run / "preflight.txt").write_text(preflight)
    (run / "cycles" / "cycle-00.json").write_text(json.dumps(cycle))
    return str(run)


def test_load_reads_the_batch_record_and_charges_an_undelivered_reset_observation(tmp_path):
    trial = {"seq": 0, "cell": "key_enter", "verdict": {"pass": True, "infra": [], "reasons": []}}
    cycle = {
        "cycle": 0,
        "setting": "screenshot+a11y",
        "boot": {"t_screenshot_200": 20.0},
        "reset_observation": {
            "screenshot_attempts": [{"status": 200}],
            "screenshot_ok": True,
            "accessibility_attempts": [{"error": "closed"}, {"error": "refused"}, {"error": "x"}],
            "accessibility_ok": False,
        },
        "trials": [trial, dict(trial, seq=1)],
    }
    run = _write_run(tmp_path, cycle, "job_id=700\ndriver_exit=0 labelled_containers_left=0\n")
    loaded = acc.load(run)
    assert loaded["batch"] == {"driver_exit": 0, "labelled_containers_left": 0}
    first, second = loaded["sessions"][0]["trials"]
    assert not first["pass"] and first["infra"] == ["reset_observation"]
    # The charge is a reason of the trial too, as verdict.judge writes every other one.
    assert first["reasons"] == ["infra: reset_observation"] and not acc.restart_only(first)
    assert second["pass"]
    # A retry that delivers is reported, not charged; older records infer delivery.
    cycle["reset_observation"] = {
        "screenshot_attempts": [{"status": 500}, {"status": 200}],
        "accessibility_attempts": [{"status": 200}],
    }
    other = tmp_path / "other"
    other.mkdir()
    run = _write_run(other, cycle, "job_id=700\n")
    loaded = acc.load(run)
    assert loaded["batch"] is None
    assert loaded["sessions"][0]["reset_observation"] == {
        "delivered": True,
        "retried": ["screenshot"],
        "failed": [],
    }
    assert loaded["sessions"][0]["trials"][0]["pass"]


def test_load_counts_restarts_and_accessibility_calls(tmp_path):
    """Decision D30: each session's restarts (guard reports and NRestarts) and calls."""
    verdict = {"pass": True, "infra": [], "reasons": []}
    step = {"accessibility_attempts": [{"status": 200}]}
    trials = [
        {"seq": 0, "cell": "key_enter", "verdict": verdict, "steps": [step],
         "pre": {"server_pid": 10}, "post": {"server_pid": 10}},
        {"seq": 1, "cell": "type_plain", "steps": [step, step], "pre": {"server_pid": 10},
         "post": {"server_pid": 11},
         "verdict": {"pass": False, "infra": ["guest_server_restart"],
                     "reasons": ["infra: guest_server_restart"]}},
    ]  # fmt: skip
    cycle = {
        "cycle": 0,
        "setting": "screenshot+a11y",
        "boot": {"t_screenshot_200": 20.0},
        "start": {
            "baseline_check": {"server_pid": 10},
            "warmup": {"server_pid": 10},
            "server_unit": {"n_restarts": 0},
        },
        "reset_observation": {"accessibility_attempts": [{"status": 200}]},
        "trials": trials,
        "stop": {"final_guard": {"server_pid": 11}, "server_unit": {"n_restarts": 1}},
    }
    run = _write_run(tmp_path, cycle, "driver_exit=0 labelled_containers_left=0\n")
    session = acc.load(run)["sessions"][0]
    assert session["restarts"] == 1 and session["accessibility_calls"] == 4
    assert acc.restart_only(session["trials"][1]) and not acc.restart_only(session["trials"][0])


def _reset_cycle(reset: dict, first: dict, warmup_pid: int = 10) -> dict:
    """A screenshot-plus-accessibility session whose first trial is ``first``."""
    passing = {"pass": True, "infra": [], "reasons": []}
    return {
        "cycle": 4,
        "setting": "screenshot+a11y",
        "boot": {"t_screenshot_200": 20.0},
        "start": {
            "baseline_check": {"server_pid": 10},
            "warmup": {"server_pid": warmup_pid},
            "server_unit": {"n_restarts": 1},
        },
        "reset_observation": reset,
        "trials": [
            first,
            {"seq": 1, "cell": "type_plain", "verdict": passing, "steps": [],
             "pre": {"server_pid": 11}, "post": {"server_pid": 11}},
        ],
        "stop": {"final_guard": {"server_pid": 11}, "server_unit": {"n_restarts": 2}},
    }  # fmt: skip


TREE_LOST = {
    "screenshot_attempts": [{"status": 200}],
    "screenshot_ok": True,
    "accessibility_attempts": [{"error": "reset"}, {"error": "refused"}, {"error": "refused"}],
    "accessibility_ok": False,
}


def test_restart_only_never_excuses_a_trial_that_also_lost_its_reset_observation(tmp_path):
    """Review of 13c6790: the reset charge was in ``infra`` only, so a restart-only trial
    that also carried an undelivered reset observation (with no restart across it) was
    excused. It now counts, by its reasons and by its infrastructure types alike."""
    hit = {"seq": 0, "cell": "key_enter", "steps": [], "pre": {"server_pid": 10},
           "post": {"server_pid": 11},
           "verdict": {"pass": False, "infra": ["guest_server_restart"],
                       "reasons": ["infra: guest_server_restart"]}}  # fmt: skip
    done = "driver_exit=0 labelled_containers_left=0\n"
    loaded = acc.load(_write_run(tmp_path, _reset_cycle(TREE_LOST, hit), done))
    first = loaded["sessions"][0]["trials"][0]
    assert first["infra"] == ["guest_server_restart", "reset_observation"]
    assert "infra: reset_observation" in first["reasons"] and not first["reset_restart"]
    assert not acc.restart_only(first)
    # Either check alone refuses it: a record whose reasons omit the charge still counts.
    stale = dict(first, reasons=["infra: guest_server_restart"])
    assert not acc.restart_only(stale)


def test_a_restart_across_the_reset_observation_is_excused_only_for_its_tree(tmp_path):
    """Decision D30 (design decision 40): the server restarted between the warm-up and the
    first pre guard and only the reset observation's tree was lost: the same fault A4
    excuses inside an entry. A lost screenshot, an unknown server id or any other reason
    in that trial still counts."""
    clean = {
        "seq": 0,
        "cell": "key_enter",
        "steps": [],
        "pre": {"server_pid": 11},
        "post": {"server_pid": 11},
        "verdict": {"pass": True, "infra": [], "reasons": []},
    }
    done = "driver_exit=0 labelled_containers_left=0\n"

    def first(tmp, reset, trial, warmup_pid=10):
        tmp.mkdir()
        session = acc.load(_write_run(tmp, _reset_cycle(reset, trial, warmup_pid), done))
        return session["sessions"][0]["trials"][0], session["sessions"][0]

    excused, session = first(tmp_path / "a", TREE_LOST, clean)
    assert excused["reset_restart"] and excused["reasons"] == ["infra: reset_observation"]
    assert acc.restart_only(excused)
    report = acc._restart_report([{"job": "9", "sessions": [session], "earlier": []}])
    assert report["trials_hit"][0]["where"] == ["reset_observation"]
    assert report["trials_hit"][0]["cycle"] == 4 and not report["trials_hit"][0]["counted"]
    # No restart across it (the warm-up already saw the new server): counted.
    same, _ = first(tmp_path / "b", TREE_LOST, clean, warmup_pid=11)
    assert not same["reset_restart"] and not acc.restart_only(same)
    # The screenshot was lost too: a restart does not excuse a lost screenshot.
    both = dict(TREE_LOST, screenshot_attempts=[{"error": "x"}] * 3, screenshot_ok=False)
    lost, _ = first(tmp_path / "c", both, clean)
    assert not lost["reset_restart"] and not acc.restart_only(lost)
    # The first pre guard could not run: decision 39's charge, never excused here.
    blind = dict(clean, pre={"error": "connection refused"})
    unknown, _ = first(tmp_path / "d", TREE_LOST, blind)
    assert not unknown["reset_restart"] and not acc.restart_only(unknown)
    # Any other reason in the trial still counts.
    wrong = dict(clean, verdict={"pass": False, "infra": [], "reasons": ["text 'a' != 'b'"]})
    other, _ = first(tmp_path / "e", TREE_LOST, wrong)
    assert other["reset_restart"] and not acc.restart_only(other)
    # A restart inside the entry as well: both are excused together.
    twice = dict(
        clean,
        post={"server_pid": 12},
        verdict={
            "pass": False,
            "infra": ["accessibility", "guest_server_restart"],
            "reasons": ["infra: accessibility", "infra: guest_server_restart"],
        },
    )
    both_hits, _ = first(tmp_path / "f", TREE_LOST, twice)
    assert acc.restart_only(both_hits)


def test_restart_report_names_sessions_and_restarts_that_hit_no_trial():
    """Section 12: every trial hit with its session, and every session whose restarts
    exceed the ones attributed to its trials."""
    halves = _a4_halves()
    halves[0]["sessions"][2]["restarts"] = 1  # e.g. during the session's start
    halves[1]["sessions"][60]["restarts"] = 2
    _hit(halves[1]["sessions"][60]["trials"][7], "infra: guest_server_restart")
    report = acc.a4(halves, 8)["guest_server"]
    assert report["restarts"] == 3
    row = report["trials_hit"][0]
    assert row["job"] == "2" and row["cycle"] == 60 and row["where"] == ["entry"]
    assert report["sessions_with_unattributed_restarts"] == [
        {"job": "1", "cycle": 2, "setting": halves[0]["sessions"][2]["setting"],
         "restarts": 1, "attributed": 0},
        {"job": "2", "cycle": 60, "setting": halves[1]["sessions"][60]["setting"],
         "restarts": 2, "attributed": 1},
    ]  # fmt: skip


def test_load_uses_the_watchers_slurm_record(tmp_path):
    trial = {"seq": 0, "cell": "key_enter", "verdict": {"pass": True, "infra": [], "reasons": []}}
    cycle = {"cycle": 0, "setting": "screenshot", "boot": {}, "trials": [trial]}
    run = _write_run(tmp_path, cycle, "driver_exit=0 labelled_containers_left=0\n")
    assert acc.load(run)["slurm"] is None
    states = tmp_path / "slurm-state"
    states.mkdir()
    (states / "700.txt").write_text("JobId=700 JobName=q2 JobState=TIMEOUT Reason=TimeLimit\n"
                                    "   ExitCode=0:15 RunTime=01:00:00\n")  # fmt: skip
    loaded = acc.load(run)
    assert loaded["slurm"] == {"state": "TIMEOUT", "exit_code": "0:15"}
    assert "TIMEOUT" in acc.counting_problems(loaded)[0]
    # An explicit reading wins; a job Slurm had forgotten leaves the batch record to decide.
    assert acc.load(run, {"state": "COMPLETED", "exit_code": "0:0"})["slurm"]["state"] == (
        "COMPLETED"
    )
    (states / "700.txt").write_text("forgotten: slurm_load_jobs error: Invalid job id\n")
    assert acc.load(run)["slurm"] is None and acc.end_state_problems(acc.load(run)) == []


# --- decision D33: restart-only trials in A1-A3 and the ladder -----------------------------------

RESTART_ONLY = ("infra: guest_server_restart",)
RESTART_AND_TREE = ("infra: accessibility", "infra: guest_server_restart")
A11Y, SHOT = "screenshot+a11y", "screenshot"


def _nth(run: dict, setting: str, cell: str, nth: int = 0) -> dict:
    """The ``nth`` trial of ``cell`` in ``setting`` (session order)."""
    found = [
        t
        for s in run["sessions"]
        if s["setting"] == setting
        for t in s["trials"]
        if t["cell"] == cell
    ]
    return found[nth]


def _a1_good() -> dict[int, list[dict]]:
    return {seed: [campaign(a1_plan(seed), job=str(seed))] for seed in (43, 44)}


def test_entry_status_never_turns_an_excused_trial_into_flaky_or_fail():
    assert acc.entry_status({A11Y: [True] * 4, SHOT: [True] * 5}, 1) == "PASS"
    assert acc.entry_status({A11Y: [True] * 3, SHOT: [True] * 5}, 2) == "RESTART_LIMIT"
    # D33: "a second excused trial in one entry counts as a failure", whichever settings
    # the two came in (the limit is per entry, not per setting).
    assert acc.entry_status({A11Y: [True] * 4, SHOT: [True] * 4}, 2) == "RESTART_LIMIT"
    # A counted failure decides as before; the excused trial changes nothing.
    assert acc.entry_status({A11Y: [True, False, True, True]}, 1) == "FLAKY"
    assert acc.entry_status({A11Y: [False] * 4}, 1) == "FAIL"
    assert acc.entry_status({}, 1) == "RESTART_LIMIT"  # no counted repetition
    # Without excused trials the section-5 reading is unchanged.
    assert acc.entry_status({A11Y: [True, False]}) == "FLAKY"
    assert acc.entry_status({A11Y: []}) == "FAIL"


@pytest.mark.parametrize("reasons", [RESTART_ONLY, RESTART_AND_TREE])
def test_a1_drops_an_excused_trial_from_its_entry_and_reports_it(reasons):
    """D33: the entry is judged on its counted repetitions (4 of 4 here, not 4 of 5, and
    never FLAKY), and the excused trial is listed in the restart report."""
    good = _a1_good()
    hit = _nth(good[43][0], A11Y, "key_enter", 2)
    _hit(hit, *reasons)
    result = acc.a1(good)
    assert result["pass"], result["problems"]
    assert result["entries"][43]["key_enter"] == "PASS"
    report = result["guest_server"][43]
    assert report["excused_trials"] == 1 and report["entries_over_restart_limit"] == []
    row = report["trials_hit"][0]
    assert (row["cell"], row["seq"], row["setting"]) == ("key_enter", hit["seq"], A11Y)
    assert row["counted"] is False and row["where"] == ["entry"]
    assert result["guest_server"][44]["trials_hit"] == []


def test_a1_fails_an_entry_on_its_second_excused_trial():
    good = _a1_good()
    _hit(_nth(good[43][0], A11Y, "key_enter", 0), *RESTART_ONLY)
    _hit(_nth(good[43][0], A11Y, "key_enter", 3), *RESTART_AND_TREE)
    result = acc.a1(good)
    assert not result["pass"]
    assert result["entries"][43]["key_enter"] == "RESTART_LIMIT"
    (over,) = result["guest_server"][43]["entries_over_restart_limit"]
    assert (over["cell"], over["status"], over["judged"]) == ("key_enter", "RESTART_LIMIT", True)
    assert [(r["job"], r["setting"]) for r in over["excused"]] == [("43", A11Y), ("43", A11Y)]
    assert any("key_enter" in p for p in result["problems"])
    # The limit is per entry (D33), not per setting or per seed: one excused trial in each
    # setting, or one in each seed's shuffle, is a second excused trial in that entry.
    split = _a1_good()
    _hit(_nth(split[43][0], A11Y, "key_enter", 0), *RESTART_ONLY)
    _hit(_nth(split[43][0], SHOT, "key_enter", 1), *RESTART_ONLY)
    result = acc.a1(split)
    assert not result["pass"] and result["entries"][43]["key_enter"] == "RESTART_LIMIT"
    seeds = _a1_good()
    _hit(_nth(seeds[43][0], A11Y, "key_enter", 0), *RESTART_ONLY)
    _hit(_nth(seeds[44][0], A11Y, "key_enter", 4), *RESTART_ONLY)
    result = acc.a1(seeds)
    assert not result["pass"]
    assert result["entries"][43]["key_enter"] == result["entries"][44]["key_enter"]
    assert result["entries"][44]["key_enter"] == "RESTART_LIMIT"
    # One excused trial in each of two entries is within the limit.
    two = _a1_good()
    _hit(_nth(two[43][0], A11Y, "key_enter", 0), *RESTART_ONLY)
    _hit(_nth(two[44][0], A11Y, "type_plain", 0), *RESTART_ONLY)
    result = acc.a1(two)
    assert result["pass"], result["problems"]
    assert result["entries"][43]["key_enter"] == result["entries"][44]["type_plain"] == "PASS"
    # A non-gating entry over the limit is reported, not gating.
    soft = _a1_good()
    _hit(_nth(soft[43][0], A11Y, "click_button_back", 0), *RESTART_ONLY)
    _hit(_nth(soft[43][0], A11Y, "click_button_back", 1), *RESTART_ONLY)
    result = acc.a1(soft)
    assert result["pass"] and result["entries"][43]["click_button_back"] == "RESTART_LIMIT"


@pytest.mark.parametrize(
    "reasons",
    [
        ("infra: execute", "infra: guest_server_restart"),  # during /execute
        ("infra: guard_script", "infra: guest_server_restart"),  # during a guard
        ("infra: guest_server_restart", "infra: screenshot"),  # slower than the retries
        ("infra: guest_server_restart", "text 'a' != 'b'"),
    ],
)
def test_a1_to_a3_still_count_a_restart_outside_an_observation_call(reasons):
    good = _a1_good()
    _hit(_nth(good[44][0], A11Y, "key_enter", 1), *reasons)
    result = acc.a1(good)
    assert not result["pass"] and result["entries"][44]["key_enter"] == "FLAKY"
    assert result["guest_server"][44]["trials_hit"][0]["counted"] is True
    stress = {
        layer: [campaign(order.plan(
            [i for i in ids(layer) if i in order.STRESS_ENTRIES], 43, 30, list(order.SETTINGS),
            acceptance=True,
        ), job=layer)]
        for layer in acc.C3_LAYERS
    }  # fmt: skip
    assert acc.a3(stress)["pass"]
    _hit(_nth(stress["H-GA"][0], A11Y, "drag_short", 4), *reasons)
    assert not acc.a3(stress)["pass"]


def test_a1_and_the_ladder_excuse_a_restart_across_the_reset_observation():
    """D33: a restart during the reset observation that left only its tree undelivered is
    excused the same way as one inside an entry (``reset_restart``); the same lost tree
    with no restart across it still counts."""
    good = _a1_good()
    session = next(s for s in good[44][0]["sessions"] if s["setting"] == A11Y)
    first = session["trials"][0]
    _hit(first, "infra: reset_observation")
    first["reset_restart"] = True
    result = acc.a1(good)
    assert result["pass"], result["problems"]
    assert result["entries"][44][first["cell"]] == "PASS"
    row = result["guest_server"][44]["trials_hit"][0]
    assert row["where"] == ["reset_observation"] and row["counted"] is False
    assert result["guest_server"][44]["excused_trials"] == 1
    first["reset_restart"] = False  # the tree was lost without a restart across it
    result = acc.a1(good)
    assert not result["pass"] and result["entries"][44][first["cell"]] == "FLAKY"
    a1 = [campaign(a1_plan(43)), campaign(a1_plan(44))]
    run = _rung(8)
    lead = next(s for s in run["sessions"] if s["setting"] == A11Y)["trials"][0]
    _hit(lead, "infra: reset_observation")
    lead["reset_restart"] = True
    result = acc.n_star(a1, {8: [run]})
    assert result["n_star"] == 8, result["rungs"][8]["problems"]
    assert result["rungs"][8]["excused_trials"] == 1


def test_a1_excused_trials_count_toward_the_limit_over_every_attempt():
    """A rerun never resets the count: an earlier attempt's excused trial and the counting
    attempt's in the same entry and setting make two (section 6.1)."""
    good = _a1_good()
    earlier = copy.deepcopy(good[43][0])
    earlier["job"], earlier["batch"], earlier["slurm"] = "42", None, None
    earlier["sessions"] = earlier["sessions"][:9]  # screenshot sessions come first
    first = earlier["sessions"][0]["trials"][0]
    _hit(first, *RESTART_ONLY)
    good[43][0]["earlier"] = [earlier]
    result = acc.a1(good)
    assert result["pass"], result["problems"]  # one excused trial: within the limit
    assert result["guest_server"][43]["excused_trials"] == 1
    _hit(_nth(good[43][0], SHOT, first["cell"], 4), *RESTART_ONLY)
    result = acc.a1(good)
    assert not result["pass"] and result["entries"][43][first["cell"]] == "RESTART_LIMIT"


def test_a1_and_a2_count_an_earlier_attempts_failures_only_on_the_cells_they_judge():
    """Section 6.1, "exactly as if the attempt had counted": a non-gating (A1) or
    outside-spec (A2) failure in an earlier attempt is reported, not counted; a gating
    one, or an in-spec one, still counts; an excused one does not."""
    good = _a1_good()
    earlier = copy.deepcopy(good[44][0])
    earlier["job"], earlier["batch"], earlier["slurm"] = "41", None, None
    _nth(earlier, SHOT, "click_button_back", 0)["pass"] = False
    good[44][0]["earlier"] = [earlier]
    assert acc.a1(good)["pass"]
    _hit(_nth(earlier, A11Y, "key_enter", 0), *RESTART_ONLY)
    assert acc.a1(good)["pass"]
    _hit(_nth(earlier, A11Y, "key_enter", 0), "infra: execute", "infra: guest_server_restart")
    result = acc.a1(good)
    assert not result["pass"] and any("earlier attempt 41" in p for p in result["problems"])

    def plan(layer):
        return order.plan(ids(layer), 43, 5, list(order.SETTINGS), acceptance=True)

    harnesses = ("H-OSW-fixed", "H-GA")
    runs = {layer: [campaign(plan(layer), job=layer, fail={"R03"})] for layer in harnesses}
    assert acc.a2(runs)["pass"]  # R03 is outside both harnesses' specs
    rerun = copy.deepcopy(runs["H-GA"][0])
    rerun["job"] = "rerun"
    cut = copy.deepcopy(runs["H-GA"][0])
    cut["job"], cut["batch"], cut["slurm"] = "cut", None, None
    rerun["earlier"] = [cut]
    assert acc.a2(dict(runs, **{"H-GA": [rerun]}))["pass"]
    _nth(cut, SHOT, "R01", 0)["pass"] = False  # in spec (gating)
    assert not acc.a2(dict(runs, **{"H-GA": [rerun]}))["pass"]


def test_a2_and_a3_judge_entries_on_their_counted_repetitions():
    def plan(layer):
        return order.plan(ids(layer), 43, 5, list(order.SETTINGS), acceptance=True)

    good = {layer: [campaign(plan(layer), job=layer)] for layer in ("H-OSW-fixed", "H-GA")}
    _hit(_nth(good["H-OSW-fixed"][0], A11Y, "R08", 0), *RESTART_AND_TREE)
    result = acc.a2(good)
    assert result["pass"] and result["cells"]["H-OSW-fixed"]["R08"] == "PASS"
    assert result["guest_server"]["H-OSW-fixed"]["excused_trials"] == 1
    _hit(_nth(good["H-OSW-fixed"][0], A11Y, "R08", 1), *RESTART_ONLY)
    result = acc.a2(good)
    assert not result["pass"] and result["cells"]["H-OSW-fixed"]["R08"] == "RESTART_LIMIT"

    def stress(layer):
        return order.plan(
            [i for i in ids(layer) if i in order.STRESS_ENTRIES], 43, 30, list(order.SETTINGS),
            acceptance=True,
        )  # fmt: skip

    runs = {layer: [campaign(stress(layer), job=layer)] for layer in acc.C3_LAYERS}
    _hit(_nth(runs["L0-fixed"][0], A11Y, "type_long_500", 17), *RESTART_ONLY)
    _hit(_nth(runs["H-GA"][0], A11Y, "type_long_500", 17), *RESTART_ONLY)  # another layer
    result = acc.a3(runs)
    assert result["pass"] and result["entries"]["L0-fixed"]["type_long_500"] == "PASS"
    assert result["entries"]["H-GA"]["type_long_500"] == "PASS"
    assert len(result["guest_server"]["L0-fixed"]["trials_hit"]) == 1
    # A second excused trial in the entry, in either setting, fails it (59 of 60 counted).
    _hit(_nth(runs["L0-fixed"][0], SHOT, "type_long_500", 3), *RESTART_ONLY)
    result = acc.a3(runs)
    assert not result["pass"]
    assert result["entries"]["L0-fixed"]["type_long_500"] == "RESTART_LIMIT"
    over = result["guest_server"]["L0-fixed"]["entries_over_restart_limit"]
    assert [(row["cell"], len(row["excused"])) for row in over] == [("type_long_500", 2)]
    assert result["guest_server"]["H-GA"]["entries_over_restart_limit"] == []


def _rung(n: int, **kwargs) -> dict:
    plan = order.plan(ids("L0-fixed"), 43, ladder_reps(n), list(order.SETTINGS), acceptance=True)
    return campaign(plan, job=str(100 + n), concurrency=n, **kwargs)


def test_a_rung_reads_its_counted_gating_trials_and_allows_two_excused():
    a1 = [campaign(a1_plan(43)), campaign(a1_plan(44))]
    run = _rung(8)
    _hit(_nth(run, A11Y, "key_enter", 0), *RESTART_ONLY)
    _hit(_nth(run, A11Y, "click_button_back", 2), *RESTART_AND_TREE)  # not gating
    result = acc.n_star(a1, {8: [run]})
    assert result["n_star"] == 8, result["rungs"][8]["problems"]
    rung = result["rungs"][8]
    assert rung["excused_trials"] == 2 and len(rung["guest_server"]["trials_hit"]) == 2
    # Two excused in one gating entry are allowed (the rung has no per-entry limit).
    _hit(_nth(run, A11Y, "click_button_back", 2), "text 'a' != 'b'")  # non-gating: reported
    _hit(_nth(run, A11Y, "key_enter", 1), *RESTART_ONLY)
    assert acc.n_star(a1, {8: [run]})["n_star"] == 8
    # A third excused trial, gating or not, leaves the rung unqualified.
    _hit(_nth(run, SHOT, "click_button_back", 0), *RESTART_ONLY)
    result = acc.n_star(a1, {8: [run]})
    assert result["n_star"] == 1 and "3 excused trials" in result["rungs"][8]["problems"][-1]
    # A restart during /execute in a gating trial counts.
    other = _rung(8)
    _hit(_nth(other, A11Y, "key_enter", 0), "infra: execute", "infra: guest_server_restart")
    result = acc.n_star(a1, {8: [other]})
    assert result["n_star"] == 1 and "gating entries not PASS" in result["rungs"][8]["problems"][0]


def test_excused_trials_steps_stay_in_the_rung_step_p95():
    a1 = [campaign(a1_plan(43)), campaign(a1_plan(44))]
    run = _rung(8)
    for nth in (0, 1):
        trial = _nth(run, A11Y, "key_enter", nth)
        _hit(trial, *RESTART_ONLY)
        trial["steps_s"] = [9.0] * 200  # 400 of 1,598 step times
    rung = acc.n_star(a1, {8: [run]})["rungs"][8]
    assert rung["excused_trials"] == 2 and rung["step_p95_s"] == 9.0
    assert not rung["qualifies"] and "step p95" in rung["problems"][0]


def test_a_rung_counts_excused_trials_over_its_attempts_but_not_an_aborted_one():
    a1 = [campaign(a1_plan(43)), campaign(a1_plan(44))]
    # A foreign-load abort is unchanged: its trials, excused ones too, do not count.
    aborted = _rung(8)
    aborted["job"] = "90"
    aborted["sessions"][1]["snapshots"][1]["squeue_foreign"] = [["91", "u", "RUNNING", "2"]]
    for nth in range(3):
        _hit(_nth(aborted, A11Y, "key_enter", nth), *RESTART_ONLY)
    rerun = dict(_rung(8), earlier=[aborted])
    _hit(_nth(rerun, A11Y, "type_plain", 0), *RESTART_ONLY)
    result = acc.n_star(a1, {8: [rerun]})
    assert result["n_star"] == 8, result["rungs"][8]["problems"]
    assert result["rungs"][8]["earlier_attempts"][0]["excused_trials"] == 3
    # An attempt that did not count (no abort) keeps its excused trials in the count.
    cut = _rung(8)
    cut["job"], cut["batch"], cut["slurm"] = "92", None, None
    cut["sessions"] = cut["sessions"][:6]  # screenshot sessions come first
    for nth in range(2):
        _hit(_nth(cut, SHOT, "type_plain", nth), *RESTART_ONLY)
    again = dict(_rung(8), earlier=[cut])
    _hit(_nth(again, SHOT, "type_plain", 0), *RESTART_ONLY)
    result = acc.n_star(a1, {8: [again]})
    assert result["n_star"] == 1 and "3 excused trials" in result["rungs"][8]["problems"][-1]


# --- review of the D33 pass: reruns of the controls and rungs without host snapshots ------------


def _uncounted(run: dict, job: str) -> dict:
    """``run`` as an earlier attempt that did not count (the job never recorded its end)."""
    earlier = copy.deepcopy(run)
    earlier["job"], earlier["batch"], earlier["slurm"] = job, None, None
    return earlier


def _without_snapshots(run: dict, sessions: slice = slice(None)) -> dict:
    """``run`` with the host snapshots of ``sessions`` missing (their record files)."""
    out = copy.deepcopy(run)
    for session in out["sessions"][sessions]:
        session["snapshots"] = [None, None]
    return out


def test_a_rung_attempt_without_host_snapshots_is_not_an_abort():
    """Section 9: only a foreign job starting, or foreign jobs holding more than 8 CPUs,
    abort a rung. An attempt missing its host snapshots cannot show that no abort
    occurred, so it does not qualify and may be rerun, but its failed and excused trials
    count (section 6.1). Before, "no host snapshots" was read as an abort and dropped
    them, so a rerun of an attempt that had counted qualified."""
    a1 = [campaign(a1_plan(43)), campaign(a1_plan(44))]
    gating = set(
        json.loads((ROOT / "harness/q2/action_path/gating_set.json").read_text())["gating"]
    )
    blind = _without_snapshots(_rung(8))
    blind["job"] = "81"
    assert acc.counting_problems(blind) == [] and acc.foreign_abort(blind) == []
    assert "missing for 20 of 20 sessions" in acc.snapshot_problems(blind)[0]
    # Alone it does not qualify, and it is not reported as aborted.
    result = acc.n_star(a1, {8: [blind]})["rungs"][8]
    assert not result["qualifies"] and not result["aborted"] and result["abort_reasons"] == []
    assert any("host snapshots missing" in p for p in result["problems"])
    # It may be rerun, and a clean one leaves the rerun free to qualify.
    rerun = dict(_rung(8), earlier=[blind])
    result = acc.n_star(a1, {8: [rerun]})
    assert result["n_star"] == 8, result["rungs"][8]["problems"]
    report = result["rungs"][8]["earlier_attempts"][0]
    assert report["abort_reasons"] == [] and report["snapshot_problems"]
    # Its gating failure counts against the rerun.
    gating_trial = next(t for s in blind["sessions"] for t in s["trials"] if t["cell"] in gating)
    _hit(gating_trial, "events differ: expected [...], observed []")
    result = acc.n_star(a1, {8: [rerun]})
    problems = result["rungs"][8]["problems"]
    assert result["n_star"] == 1 and any("earlier attempt 81 has 1 failed" in p for p in problems)
    assert not any("counted and was rerun" in p for p in problems)
    # So do its excused trials, toward the rung's limit of two.
    gating_trial["pass"], gating_trial["infra"], gating_trial["reasons"] = True, [], []
    for nth in range(3):
        _hit(_nth(blind, A11Y, "type_plain", nth), *RESTART_ONLY)
    result = acc.n_star(a1, {8: [rerun]})
    assert result["n_star"] == 1
    assert "3 excused trials" in result["rungs"][8]["problems"][-1]
    # A counting attempt missing one session's snapshots does not qualify either.
    partial = _without_snapshots(_rung(8), slice(3, 4))
    assert acc.foreign_abort(partial) == []
    assert "missing for 1 of 20 sessions, first [3]" in acc.snapshot_problems(partial)[0]
    assert acc.n_star(a1, {8: [partial]})["n_star"] == 1
    # A foreign-load abort still drops the aborted attempt's trials (section 9).
    aborted = copy.deepcopy(blind)
    aborted["sessions"][0]["snapshots"] = [
        {"t": 0.0, "squeue_foreign": []},
        {"t": 1.0, "squeue_foreign": [["91", "u", "RUNNING", "2"]]},
    ]
    assert acc.foreign_abort(aborted) == ["foreign job started: ['91']"]
    assert acc.n_star(a1, {8: [dict(_rung(8), earlier=[aborted])]})["n_star"] == 8


def test_c1_reads_an_earlier_attempt_by_its_own_rule():
    """C1's known-defect cells fail by design: an earlier attempt's failures there are
    what C1 requires and never count against it, and C1 judges no other cell; a
    known-defect cell that passed in an earlier attempt does count."""

    def plan(layer):
        return order.plan(ids(layer), 42, 5, ["screenshot"])

    defects = {layer: frozenset(cells) for layer, cells in acc.C1_MUST_FAIL.items()}
    good = {layer: [campaign(plan(layer), fail=defects[layer])] for layer in acc.C1_MUST_FAIL}
    first = _uncounted(good["H-OSW-up"][0], "70")
    first["slurm"] = {"state": "TIMEOUT", "exit_code": "0:15"}
    first["sessions"] = first["sessions"][:1]
    _nth(first, SHOT, "R13", 0)["pass"] = False  # not a cell C1 judges
    rerun = dict(good, **{"H-OSW-up": [dict(copy.deepcopy(good["H-OSW-up"][0]), earlier=[first])]})
    assert acc.c1(rerun)["pass"], acc.c1(rerun)["problems"]
    _nth(first, SHOT, "R09", 0)["pass"] = True  # the defect did not show in that trial
    result = acc.c1(rerun)
    assert not result["pass"]
    assert any(
        "earlier attempt 70 passed known-defect cells ['R09']" in p for p in result["problems"]
    )
    # The rerun rules still hold: a campaign that counted is not rerun.
    counted = dict(good, **{"H-GA-buggy": [dict(good["H-GA-buggy"][0], earlier=[
        copy.deepcopy(good["H-GA-buggy"][0])
    ])]})  # fmt: skip
    assert not acc.c1(counted)["pass"]


def test_c2_reads_an_earlier_attempt_as_it_reads_the_counting_one():
    """An earlier failure counts against C2 only on a cell outside the predicted set,
    under C2's own reading of the trial (decision 34); the predicted cells fail by
    design."""
    plan = _c2_plan()
    good = _c2_campaign(plan, lambda t: None)
    first = _uncounted(good, "79")
    first["receipt"]["summary"]["infra_gates_pass"] = False
    rerun = dict(copy.deepcopy(good), earlier=[first])
    assert acc.c2([rerun])["pass"], acc.c2([rerun])["problems"]
    # A marker-only failure outside the predicted set is not a failure under C2's reading.
    stale = _nth(first, SHOT, "type_plain", 0)
    stale["pass"], stale["reasons"] = False, ["marker [3, 1] != probe final [3, 2]"]
    assert acc.c2([rerun])["pass"]
    # A text difference there is, and so is an infrastructure failure.
    stale["reasons"] = ["text 'a' != 'b'"]
    result = acc.c2([rerun])
    assert not result["pass"] and "earlier attempt 79 has 1 failed" in result["problems"][0]
    stale["reasons"], stale["infra"] = ["infra: execute"], ["execute"]
    assert not acc.c2([rerun])["pass"]


def test_c3_reads_kills_from_the_counting_attempt_and_the_reference_over_every_attempt():
    """A mutant's failures are its kills, so an earlier attempt's never count against C3;
    its kills come from the counting attempt and the earlier attempt is reported (its
    streams decide equivalence only, decision D39). A cell the reference failed in any
    attempt cannot kill, while a by-design outside-spec failure in an earlier reference
    attempt costs nothing."""
    import yaml

    from harness.q2.action_path import mutants as kit

    operators = yaml.safe_load(
        (ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text()
    )
    pairs = kit.scored_pairs(operators)
    plans = {layer: order.plan(ids(layer), 42, 1, ["screenshot"]) for layer in acc.C3_LAYERS}
    references = {layer: [campaign(plans[layer])] for layer in acc.C3_LAYERS}
    runs = {(op, layer): [campaign(plans[layer], fail={"R14", "key_enter"})] for op, layer in pairs}
    op = next(p for p in pairs if p[1] == "H-GA")
    key = f"{op[0]} H-GA"
    one = runs[op][0]
    rerun = {**runs, op: [dict(copy.deepcopy(one), earlier=[_uncounted(one, "e3")])]}
    result = acc.c3(rerun, references)
    assert result["pass"], result["problems"]
    entry = result["mutants"][key]
    assert entry["outcome"] == "killed" and entry["killers"] == ["R14", "key_enter"]
    assert entry["earlier_attempts"] == [
        {
            "job": "e3",
            "failed_cells": ["R14", "key_enter"],
            "signature_matches_reference": True,
            "differing_cells": [],
            "infra_cells_not_compared": [],
        }
    ]  # the synthetic failures keep the reference's events and text
    # An earlier attempt's kills do not count: a counting attempt that kills nothing and
    # differs from the reference survives.
    differs = campaign(plans["H-GA"])
    _nth(differs, SHOT, "type_plain", 0)["text"] = "b"
    survivor = {**runs, op: [dict(differs, earlier=[_uncounted(one, "e4")])]}
    result = acc.c3(survivor, references)
    assert not result["pass"] and result["mutants"][key]["outcome"] == "survived"
    # The reference: an outside-spec failure in an earlier attempt (R03, by design on
    # H-GA) costs nothing; a failure of a cell that can kill keeps it from killing.
    reference = references["H-GA"][0]
    earlier_reference = _uncounted(reference, "r1")
    _nth(earlier_reference, SHOT, "R03", 0)["pass"] = False
    rerun_reference = dict(references, **{"H-GA": [dict(reference, earlier=[earlier_reference])]})
    assert acc.c3(runs, rerun_reference)["pass"]
    _nth(earlier_reference, SHOT, "key_enter", 0)["pass"] = False
    result = acc.c3(runs, rerun_reference)
    entry = result["mutants"][key]
    assert entry["killers"] == ["R14"] and entry["reference_not_clean"] == ["key_enter"]
    alone = campaign(plans["H-GA"], fail={"key_enter"})
    _nth(alone, SHOT, "key_enter", 0)["text"] = "b"  # the mutant's own effect
    lone = {**runs, op: [alone]}
    assert acc.c3(lone, references)["mutants"][key]["outcome"] == "killed"
    result = acc.c3(lone, rerun_reference)
    assert not result["pass"] and result["mutants"][key]["outcome"] == "survived"
    assert result["mutants"][key]["reference_not_clean"] == ["key_enter"]


def test_c4_counts_an_earlier_a1_attempts_mismatch():
    """C4 reads the tap's stream, which A1 does not judge for an entry the probe
    observes, so an earlier attempt's projection mismatch must count (section 6.1)."""
    counting = campaign(a1_plan(43))
    _nth(counting, SHOT, "key_enter", 0)["c4"] = True
    earlier = _uncounted(counting, "43a")
    earlier["sessions"] = earlier["sessions"][:2]
    counting["earlier"] = [earlier]
    result = acc.c4([counting])
    assert result["pass"] and result["trials_checked"] == 2
    _nth(earlier, SHOT, "key_enter", 0)["c4"] = False
    result = acc.c4([counting])
    assert not result["pass"] and result["problems"] == ["job 43a screenshot key_enter"]


# --- wording and reporting closed before the freeze (main section 22) --------------------------


def test_entries_over_the_restart_limit_are_listed_whatever_their_status():
    """Section 12: every entry with two or more excused trials is listed with its excused
    repetitions, also when a counted failure made it FLAKY or FAIL first, and also when
    the criterion does not judge it; in A1 the repetitions are pooled over both seeds."""
    good = _a1_good()
    for nth in (0, 1):
        _hit(_nth(good[43][0], A11Y, "key_enter", nth), *RESTART_ONLY)
    _nth(good[43][0], SHOT, "key_enter", 2)["pass"] = False  # a counted failure as well
    result = acc.a1(good)
    assert not result["pass"] and result["entries"][43]["key_enter"] == "FLAKY"
    (over,) = result["guest_server"][43]["entries_over_restart_limit"]
    assert (over["cell"], over["status"], len(over["excused"])) == ("key_enter", "FLAKY", 2)
    # A non-gating entry over the limit is listed and marked as not judged.
    soft = _a1_good()
    for nth in (0, 1):
        _hit(_nth(soft[44][0], SHOT, "click_button_back", nth), *RESTART_ONLY)
    result = acc.a1(soft)
    assert result["pass"]
    (over,) = result["guest_server"][44]["entries_over_restart_limit"]
    assert over["cell"] == "click_button_back" and over["judged"] is False
    # One excused trial in each seed's shuffle: listed under both seeds, with both.
    seeds = _a1_good()
    _hit(_nth(seeds[43][0], A11Y, "type_plain", 0), *RESTART_ONLY)
    _hit(_nth(seeds[44][0], SHOT, "type_plain", 3), *RESTART_AND_TREE)
    result = acc.a1(seeds)
    for seed in (43, 44):
        (over,) = result["guest_server"][seed]["entries_over_restart_limit"]
        assert over["status"] == "RESTART_LIMIT"
        assert sorted((r["job"], r["setting"]) for r in over["excused"]) == [
            ("43", A11Y), ("44", SHOT)
        ]  # fmt: skip
    # One excused trial is within the limit and not listed.
    one = _a1_good()
    _hit(_nth(one[43][0], A11Y, "key_enter", 0), *RESTART_ONLY)
    assert acc.a1(one)["guest_server"][43]["entries_over_restart_limit"] == []


def test_a4_counts_its_excused_trials_over_every_attempt():
    """Section 12: A4 reports its excused trials over every attempt, as the other
    criteria do, and those of the counting attempts beside them."""
    halves = _a4_halves()
    earlier = copy.deepcopy(halves[0])
    earlier["job"], earlier["batch"], earlier["slurm"] = "0", None, None
    earlier["sessions"] = earlier["sessions"][:4]
    _hit(earlier["sessions"][1]["trials"][2], *RESTART_ONLY)
    halves[0]["earlier"] = [earlier]
    _hit(halves[1]["sessions"][60]["trials"][7], *RESTART_AND_TREE)
    result = acc.a4(halves, 8)
    assert result["pass"], result["problems"]
    assert result["restart_only_trials"] == 2 and result["restart_only_trials_counting"] == 1


def test_a4_reports_its_restart_rate_against_a7s_bound_under_a_repair_attempt():
    """A7 runs under attempt 1 only, so under a repair attempt A4 reports its own
    restarts per accessibility call against A7's bound, on A7's rule (restarts of every
    attempt, calls of the counting attempts), reported and not judged."""
    halves = _a4_halves()
    for c in halves:
        for session in c["sessions"]:
            session["accessibility_calls"] = 68 if session["setting"] == A11Y else 0
    calls = sum(s["accessibility_calls"] for c in halves for s in c["sessions"])
    assert acc.a4(halves, 8)["repair_restart_rate"] is None  # attempt 1: A7 judges it
    for c in halves:
        c["manifest"]["workload"]["attempt"] = 2
    a11y = [s for c in halves for s in c["sessions"] if s["setting"] == A11Y]
    assert calls == 534 * 68
    for session in a11y[:6]:
        session["restarts"] = 1
    earlier = copy.deepcopy(halves[0])
    earlier["job"], earlier["batch"], earlier["slurm"] = "0", None, None
    earlier["sessions"] = [copy.deepcopy(a11y[20])]
    earlier["sessions"][0]["restarts"] = 2
    halves[0]["earlier"] = [earlier]
    result = acc.a4(halves, 8)
    assert result["pass"], result["problems"]  # reported, never judged
    rate = result["repair_restart_rate"]
    assert rate["attempt"] == 2 and rate["judged"] is False
    assert rate["restarts"] == 8 and rate["restarts_accessibility_setting"] == 8
    assert rate["accessibility_calls"] == calls  # the earlier attempt's calls are not added
    assert rate["upper_95"] == pytest.approx(acc.poisson_upper(8) / calls)
    assert rate["bound"] == acc.OBSERVATION_BOUND and rate["within_bound"] is True
    # Over A7's bound: still reported only, and a restart in a screenshot-setting session
    # counts toward the rate as well.
    shot = next(s for s in halves[1]["sessions"] if s["setting"] == SHOT)
    shot["restarts"] = 1
    for session in a11y[:40]:
        session["restarts"] = 1
    result = acc.a4(halves, 8)
    rate = result["repair_restart_rate"]
    assert result["pass"] and rate["within_bound"] is False
    assert rate["restarts"] == 43 and rate["restarts_accessibility_setting"] == 42


def test_a5_reports_earlier_attempts_receipts_without_judging_them():
    """A5 judges the counting attempts' receipts; an earlier attempt's is reported (a
    killed job can leave labelled containers by design, and writes no receipt)."""
    reset = campaign([], job="5")
    reset["receipt"]["summary"].update(sentinel_reset_checks=20, sentinel_pristine=20)
    other = campaign([], job="6")
    killed = _uncounted(other, "4")
    killed["receipt"] = {}
    dirty = _uncounted(other, "3")
    dirty["receipt"]["labelled_containers_left"] = ["c"]
    rerun = dict(other, earlier=[killed])
    reset_rerun = dict(reset, earlier=[dirty])
    result = acc.a5(reset_rerun, [rerun], "a" * 40)
    assert result["pass"], result["problems"]
    rows = {row["job"]: row for row in result["earlier_attempts"]}
    assert rows["4"]["receipt"] is False and rows["4"]["rerun_as"] == "6"
    assert rows["3"]["labelled_containers_left"] == ["c"] and rows["3"]["rerun_as"] == "5"
    # The counting attempt's own receipt is still judged.
    rerun["receipt"] = dict(rerun["receipt"], qcow2_unchanged=False)
    assert not acc.a5(reset_rerun, [rerun], "a" * 40)["pass"]


def test_load_reads_an_attempt_killed_before_its_driver_wrote_a_receipt(tmp_path):
    """The driver writes receipt.json last, so a job ended by a signal, a time limit or a
    node failure has none (development runs 695-699). Such an attempt must load: it
    cannot count, its job id comes from the batch script's preflight record, and its
    finished sessions' failed trials count against a rerun (section 6.1)."""
    failing = {"pass": False, "infra": [], "reasons": ["text 'a' != 'b'"]}
    cycle = {
        "cycle": 0,
        "setting": "screenshot",
        "boot": {"t_screenshot_200": 20.0},
        "trials": [{"seq": 0, "cell": "key_enter", "verdict": failing}],
    }
    run = _write_run(tmp_path, cycle, "job_id=695\nbatch_sha256=x\n")
    os.remove(os.path.join(run, "receipt.json"))
    killed = acc.load(run)
    assert killed["job"] == "695" and killed["receipt"] == {} and killed["batch"] is None
    problems = acc.counting_problems(killed)
    assert any("end state unknown" in p for p in problems)
    assert any("infra_gates_pass is not true" in p for p in problems)
    assert acc.failed_trials(killed) == [("screenshot", 0, "key_enter")]
    # As an earlier attempt it may be rerun, and its gating failure counts.
    rerun = dict(campaign(a1_plan(43), job="709"), earlier=[killed])
    result = acc.a1({43: [rerun], 44: [campaign(a1_plan(44), job="710")]})
    assert not result["pass"]
    assert any("earlier attempt 695 has 1 failed" in p for p in result["problems"])
    assert not any("counted and was rerun" in p for p in result["problems"])
    # A job killed while its first VM booted has no finished session at all.
    booting = tmp_path / "booting" / "696"
    (booting / "cycles").mkdir(parents=True)
    (booting / "manifest.json").write_text(json.dumps({"vm": {"concurrency": 1}}))
    (booting / "cycles" / "cycle-00.trials.jsonl").write_text('{"seq": 0}\n')
    loaded = acc.load(str(booting))
    assert loaded["job"] == "696" and loaded["sessions"] == []  # named after its directory
    assert acc.counting_problems(loaded)


# --- decision D39: C3 equivalence fails closed; unparseable run files (main section 23) ---------


def _c3_setup() -> tuple[dict, dict, tuple[str, str], dict]:
    """Every scored mutant killed, the L0-fixed references and one L0-fixed operator."""
    import yaml

    from harness.q2.action_path import mutants as kit

    operators = yaml.safe_load(
        (ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text()
    )
    pairs = kit.scored_pairs(operators)
    plans = {layer: order.plan(ids(layer), 42, 1, ["screenshot"]) for layer in acc.C3_LAYERS}
    references = {layer: [campaign(plans[layer], job=f"ref-{layer}")] for layer in acc.C3_LAYERS}
    runs = {(op, layer): [campaign(plans[layer], fail={"R14", "key_enter"})] for op, layer in pairs}
    op = next(p for p in pairs if p[1] == "L0-fixed")
    return runs, references, op, plans


def _timed_out(run: dict, job: str) -> dict:
    """``run`` as an earlier attempt that hit its time limit (it did not count)."""
    earlier = copy.deepcopy(run)
    earlier["job"], earlier["batch"] = job, None
    earlier["slurm"] = {"state": "TIMEOUT", "exit_code": "0:15"}
    return earlier


def test_c3_equivalence_needs_every_attempts_stream_to_match_the_reference():
    """Decision D39: a mutant is equivalent only if its counting attempt's signature equals
    the reference's and so does every earlier attempt's stream on each cell it ran
    without an infrastructure failure. Kills stay the counting attempt's, so cancelling
    and rerunning cannot turn a survivor (or an earlier-only kill) into an equivalent
    mutant, while an earlier difference on a cell that had an infrastructure failure
    says nothing about the mutant and does not count."""
    runs, references, op, plans = _c3_setup()
    key = f"{op[0]} L0-fixed"
    same = campaign(plans["L0-fixed"], job="mut-same")  # the reference's streams, no kill
    alone = acc.c3({**runs, op: [same]}, references)
    assert alone["pass"] and alone["mutants"][key]["outcome"] == "equivalent"
    # The final verifier's probe: an earlier TIMEOUT attempt in which type_plain passed
    # with different text. Before D39 this read as equivalent and C3 passed.
    earlier = _timed_out(same, "mut-early")
    _nth(earlier, SHOT, "type_plain", 0)["text"] = "TYPED-DIFFERENTLY"
    result = acc.c3({**runs, op: [dict(copy.deepcopy(same), earlier=[earlier])]}, references)
    entry = result["mutants"][key]
    assert not result["pass"] and entry["outcome"] == "survived" and entry["killers"] == []
    assert f"{op[0]} on L0-fixed survived and is not equivalent" in result["problems"]
    assert entry["earlier_attempts"] == [
        {
            "job": "mut-early",
            "failed_cells": [],
            "signature_matches_reference": False,
            "differing_cells": ["type_plain"],
            "infra_cells_not_compared": [],
        }
    ]
    # The outcome the same stream gets as the counting attempt: survived.
    single = dict(copy.deepcopy(earlier), job="mut-single", batch=same["batch"])
    single["slurm"] = same["slurm"]
    result = acc.c3({**runs, op: [single]}, references)
    assert not result["pass"] and result["mutants"][key]["outcome"] == "survived"
    # An earlier-only clean kill (key_enter fails without an infrastructure failure, its
    # stream differs) next to a counting attempt identical to the reference: not killed
    # (kills are the counting attempt's) and not equivalent, so it survives.
    killed_once = _timed_out(same, "mut-kill")
    trial = _nth(killed_once, SHOT, "key_enter", 0)
    trial["pass"], trial["reasons"], trial["events"] = False, ["events differ"], []
    result = acc.c3({**runs, op: [dict(copy.deepcopy(same), earlier=[killed_once])]}, references)
    entry = result["mutants"][key]
    assert not result["pass"] and entry["outcome"] == "survived" and entry["killers"] == []
    (row,) = entry["earlier_attempts"]
    assert row["failed_cells"] == ["key_enter"] and row["differing_cells"] == ["key_enter"]
    # An earlier attempt whose only differences are on cells with an infrastructure
    # failure (a lost tap window, a screenshot not delivered): still equivalent.
    lost = _timed_out(same, "mut-infra")
    for cell, kind in (("type_plain", "screenshot"), ("key_enter", "tap_window")):
        trial = _nth(lost, SHOT, cell, 0)
        trial["pass"], trial["infra"], trial["reasons"] = False, [kind], [f"infra: {kind}"]
        trial["events"], trial["text"] = [], "lost"
    result = acc.c3({**runs, op: [dict(copy.deepcopy(same), earlier=[lost])]}, references)
    entry = result["mutants"][key]
    assert result["pass"], result["problems"]
    assert entry["outcome"] == "equivalent"
    (row,) = entry["earlier_attempts"]
    assert row["differing_cells"] == [] and row["signature_matches_reference"] is False
    assert row["infra_cells_not_compared"] == ["key_enter", "type_plain"]
    # The same infrastructure failure next to a clean difference elsewhere: not equivalent.
    _nth(lost, SHOT, "click_right", 0)["text"] = "b"
    result = acc.c3({**runs, op: [dict(copy.deepcopy(same), earlier=[lost])]}, references)
    assert not result["pass"] and result["mutants"][key]["outcome"] == "survived"
    # An earlier attempt cut short compares only the cells it reached.
    short = _timed_out(same, "mut-short")
    short["sessions"] = short["sessions"][:1]
    short["sessions"][0]["trials"] = short["sessions"][0]["trials"][:5]
    result = acc.c3({**runs, op: [dict(copy.deepcopy(same), earlier=[short])]}, references)
    assert result["pass"] and result["mutants"][key]["outcome"] == "equivalent"
    # Kills are unchanged: a counting attempt that kills passes whatever its earlier
    # attempt's streams were.
    killer = runs[op][0]
    rerun = dict(copy.deepcopy(killer), earlier=[_timed_out(earlier, "mut-early-2")])
    result = acc.c3({**runs, op: [rerun]}, references)
    assert result["pass"] and result["mutants"][key]["outcome"] == "killed"


def test_load_reads_an_unparseable_run_file_as_missing(tmp_path):
    """Decision D39: a receipt, cycle or record file a kill cut short (the driver and the
    runner write them whole but not atomically) reads as missing instead of stopping the
    analysis: an empty receipt, a session not run, a session without host snapshots. The
    attempt cannot count, may be rerun, and its readable sessions' failures count."""
    failing = {"pass": False, "infra": [], "reasons": ["text 'a' != 'b'"]}
    passing = {"pass": True, "infra": [], "reasons": []}
    cycle = {
        "cycle": 0,
        "setting": "screenshot",
        "boot": {"t_screenshot_200": 20.0},
        "trials": [{"seq": 0, "cell": "key_enter", "verdict": failing}],
    }
    run = _write_run(tmp_path, cycle, "job_id=701\ndriver_exit=0 labelled_containers_left=0\n")
    receipt = {
        "job_id": "701",
        "summary": {"infra_gates_pass": True, "leaked_volumes": []},
        "qcow2_unchanged": True,
        "labelled_containers_left": [],
    }
    (Path(run) / "receipt.json").write_text(json.dumps(receipt))
    cycles = Path(run) / "cycles"
    snapshot = {"t": 1.0, "squeue_foreign": []}
    (cycles / "record-00.json").write_text(
        json.dumps({"host_before": snapshot, "host_after": dict(snapshot, t=2.0)})
    )
    intact = acc.load(run)
    assert intact["unreadable"] == [] and not acc.counting_problems(intact)
    assert intact["sessions"][0]["snapshots"][0] == snapshot
    # A record cut inside a multi-byte character: the session loads without snapshots.
    (cycles / "record-00.json").write_bytes(b'{"host_before": {"note": "\xc3')
    loaded = acc.load(run)
    assert loaded["unreadable"] == [os.path.join("cycles", "record-00.json")]
    assert loaded["sessions"][0]["snapshots"] == [None, None]
    assert any("unreadable run files" in p for p in acc.counting_problems(loaded))
    # A second session whose cycle file was cut short, and an empty receipt file.
    later = dict(cycle, cycle=1, trials=[{"seq": 0, "cell": "type_plain", "verdict": passing}])
    (cycles / "cycle-01.json").write_text(json.dumps(later)[:40])
    (cycles / "record-01.json").write_text(json.dumps({"host_before": snapshot}))
    (Path(run) / "receipt.json").write_text("")
    loaded = acc.load(run)
    assert loaded["job"] == "701" and loaded["receipt"] == {}
    assert [s["cycle"] for s in loaded["sessions"]] == [0]  # session 1 is reported as not run
    assert sorted(loaded["unreadable"]) == sorted(
        ["receipt.json", os.path.join("cycles", "cycle-01.json"),
         os.path.join("cycles", "record-00.json")]
    )  # fmt: skip
    problems = acc.counting_problems(loaded)
    assert any("infra_gates_pass is not true" in p for p in problems)
    assert any("unreadable run files" in p for p in problems)
    assert acc.failed_trials(loaded) == [("screenshot", 0, "key_enter")]
    # As an earlier attempt it may be rerun, and its readable gating failure counts.
    rerun = dict(campaign(a1_plan(43), job="709"), earlier=[loaded])
    result = acc.a1({43: [rerun], 44: [campaign(a1_plan(44), job="710")]})
    assert not result["pass"]
    assert any("earlier attempt 701 has 1 failed" in p for p in result["problems"])
    assert not any("counted and was rerun" in p for p in result["problems"])
    # A receipt that parses but is not an object reads as missing too.
    (Path(run) / "receipt.json").write_text("[]")
    assert "receipt.json" in acc.load(run)["unreadable"]
