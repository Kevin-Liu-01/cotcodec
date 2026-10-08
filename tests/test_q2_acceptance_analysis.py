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

    predicted = frozenset(
        yaml.safe_load((ROOT / "harness/q2/action_path/l0_raw_prediction.yaml").read_text())[
            "predicted_fail"
        ]
    )
    run = campaign(plan, fail=predicted)
    for session in run["sessions"]:
        for trial in session["trials"]:
            trial["reasons"] = [] if trial["pass"] else ["text 'a' != 'b'"]
            mutate(trial)
    return run


def test_c2_judges_l0_raw_on_the_event_and_text_channels_only():
    """Design decision 34: marker and release-state timing never decide C2."""
    plan = order.plan(ids("L0-fixed"), 42, 5, ["screenshot"])
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
    }
    assert loaded["sessions"][0]["trials"][0]["pass"]


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
