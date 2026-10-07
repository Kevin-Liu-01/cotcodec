"""The acceptance analysis (harness/q2/action_path/acceptance.py) on synthetic campaigns."""

from __future__ import annotations

import copy
import json
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
        "sessions": sessions,
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


def test_c2_requires_the_exact_predicted_failing_set():
    import yaml

    predicted = frozenset(
        yaml.safe_load((ROOT / "harness/q2/action_path/l0_raw_prediction.yaml").read_text())[
            "predicted_fail"
        ]
    )
    plan = order.plan(ids("L0-fixed"), 42, 5, ["screenshot"])
    assert acc.c2([campaign(plan, fail=predicted)])["pass"]
    assert not acc.c2([campaign(plan, fail=predicted | {"key_enter"})])["pass"]
    assert not acc.c2([campaign(plan, fail=predicted - {"type_emoji"})])["pass"]


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
