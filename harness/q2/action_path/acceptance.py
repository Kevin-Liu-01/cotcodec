"""Acceptance analysis of q2-action-path-v1: A1-A6, C1-C4 and the concurrency N*.

This module restates the preregistration's decision rules (sections 5-9 of
``program/preregistrations/q2-action-path-v1.md``) as code, frozen with the executor
addendum before any acceptance trial, so the verdicts are computed the way the text
says and nothing is chosen after the data. It reads campaign run directories as the
VM lane writes them (``manifest.json``, ``receipt.json``, ``cycles/cycle-NN.json``,
``cycles/record-NN.json``) and the Slurm end state of each job, which the job cannot
record about itself: the operator reads it with ``scontrol show job`` and passes it in.

Rules that apply to every criterion:

* a campaign counts only if its Slurm state is COMPLETED with exit code 0:0, its
  receipt's ``infra_gates_pass`` is true, ``System.qcow2`` is unchanged and no
  labelled container or volume was left (sections 6.1 and 7, A5);
* a trial is PASS only as ``verdict.judge`` judged it, infrastructure failures
  included (section 6.1); an entry is PASS only at k of k repetitions, and an entry
  that is PASS in one observation setting and not the other fails (section 5);
* the trials a criterion runs must be exactly the realized order its manifest
  declares (``order.plan`` or ``volume.sessions``), so a campaign cut short cannot pass.

Standard library plus the suite's own modules; Python 3.10 compatible.
"""

from __future__ import annotations

import glob
import json
import math
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from harness.q2.action_path import order

ROOT = Path(__file__).resolve().parents[3]
CELLS = ROOT / "harness/q2/action_path/suite_cells.json"
GATING = ROOT / "harness/q2/action_path/gating_set.json"
VOLUME_PLAN = ROOT / "harness/q2/action_path/volume_plan.json"
PREDICTION = ROOT / "harness/q2/action_path/l0_raw_prediction.yaml"
OPERATORS = ROOT / "harness/q2/action_path/mutation_operators.yaml"
LADDER_RUNGS = (8, 16, 24, 32, 40)
BOOT_P95_MAX_S = 180.0
STEP_P95_FACTOR = 2.0
MIN_RUNG_BOOTS = 20
FOREIGN_CPUS_MAX = 8
# Section 8, C1: the cells each detection control must fail in 5 of 5 repetitions.
C1_MUST_FAIL = {
    "H-OSW-up": ("R08", "R09", "R10", "R11"),
    "H-GA-buggy": ("R01", "R02", "R05", "R06", "R07"),
}
SETTINGS = order.SETTINGS
C3_LAYERS = ("L0-fixed", "H-OSW-fixed", "H-GA")  # the scored layers (section 8, C3)


# --- loading ----------------------------------------------------------------------------------


def _read(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load(run_dir: str, slurm: dict[str, str]) -> dict[str, Any]:
    """One campaign: manifest, receipt, Slurm end state and its sessions' trials."""
    manifest = _read(os.path.join(run_dir, "manifest.json"))
    receipt = _read(os.path.join(run_dir, "receipt.json"))
    sessions = []
    paths = glob.glob(os.path.join(run_dir, "cycles", "cycle-[0-9][0-9]*.json"))
    # Cycle numbers are plan indices; sort them as numbers (cycle-100 after cycle-99).
    for path in sorted(paths, key=lambda p: int(os.path.basename(p)[6:-5])):
        cycle = _read(path)
        record_path = path.replace("cycle-", "record-")
        record = _read(record_path) if os.path.exists(record_path) else {}
        sessions.append(
            {
                "cycle": cycle.get("cycle"),
                "setting": cycle.get("setting"),
                "boot_s": (cycle.get("boot") or {}).get("t_screenshot_200"),
                "error": cycle.get("error"),
                "trials": [_trial(t, cycle.get("setting")) for t in cycle.get("trials") or []],
                "snapshots": [record.get("host_before"), record.get("host_after")],
            }
        )
    return {
        "job": str(receipt.get("job_id")),
        "manifest": manifest,
        "receipt": receipt,
        "slurm": slurm,
        "sessions": sessions,
    }


def _trial(raw: dict[str, Any], setting: str | None) -> dict[str, Any]:
    verdict = raw.get("verdict")
    if verdict is None:  # canary trials record their own verdict
        verdict = {"pass": raw.get("pass"), "infra": raw.get("infra") or []}
    end = ((raw.get("post") or {}).get("end")) or {}
    steps = [((s.get("timing_s") or {}).get("total")) for s in raw.get("steps") or []]
    return {
        "seq": raw.get("seq"),
        "cell": raw.get("cell"),
        "setting": setting,
        "pass": bool(verdict.get("pass")),
        "infra": list(verdict.get("infra") or []),
        "retried": list(verdict.get("retried") or []),
        "c4": raw.get("c4"),
        "events": [r[:-1] for r in raw.get("tap_window") or [] if _device(r)],
        "text": end.get("text"),
        "terminal": raw.get("terminal"),
        "steps_s": [s for s in steps if isinstance(s, int | float)],
    }


def _device(record: list[Any]) -> bool:
    return bool(record) and record[0] in (
        "KeyPress", "KeyRelease", "ButtonPress", "ButtonRelease", "MotionNotify",
    )  # fmt: skip


# --- shared rules -----------------------------------------------------------------------------


def campaign_problems(campaign: dict[str, Any]) -> list[str]:
    """Why a campaign cannot count at all (empty when it can)."""
    out = []
    slurm = campaign.get("slurm") or {}
    if slurm.get("state") != "COMPLETED" or slurm.get("exit_code") != "0:0":
        out.append(f"job {campaign['job']}: Slurm {slurm.get('state')} {slurm.get('exit_code')}")
    receipt = campaign["receipt"]
    summary = receipt.get("summary") or {}
    if summary.get("infra_gates_pass") is not True:
        out.append(f"job {campaign['job']}: infra_gates_pass is not true")
    if receipt.get("qcow2_unchanged") is not True:
        out.append(f"job {campaign['job']}: System.qcow2 changed or unchecked")
    if receipt.get("labelled_containers_left") or summary.get("leaked_volumes"):
        out.append(f"job {campaign['job']}: labelled containers or volumes left")
    return out


def realized(campaign: dict[str, Any]) -> list[tuple[str, int, str]]:
    """(setting, seq, cell) of every trial the campaign ran, in session order."""
    return [
        (session["setting"], trial["seq"], trial["cell"])
        for session in campaign["sessions"]
        for trial in session["trials"]
    ]


def expected(sessions: list[dict[str, Any]]) -> list[tuple[str, int, str]]:
    return [(s["setting"], seq, cell) for s in sessions for seq, cell in s["trials"]]


def outcomes(campaigns: Iterable[dict[str, Any]]) -> dict[str, dict[str, list[bool]]]:
    """cell -> setting -> pass flags, over every trial of the campaigns."""
    out: dict[str, dict[str, list[bool]]] = {}
    for campaign in campaigns:
        for session in campaign["sessions"]:
            for trial in session["trials"]:
                out.setdefault(trial["cell"], {}).setdefault(session["setting"], []).append(
                    trial["pass"]
                )
    return out


def entry_status(flags_by_setting: dict[str, list[bool]]) -> str:
    """PASS only when every repetition in every setting passed; FAIL when none did."""
    flags = [f for values in flags_by_setting.values() for f in values]
    if flags and all(flags):
        return "PASS"
    return "FAIL" if not any(flags) else "FLAKY"


def _gating() -> set[str]:
    return set(json.loads(GATING.read_text(encoding="utf-8"))["gating"])


def _cells() -> dict[str, Any]:
    return json.loads(CELLS.read_text(encoding="utf-8"))


def _verdict(problems: list[str], extra: dict[str, Any]) -> dict[str, Any]:
    return {"pass": not problems, "problems": problems, **extra}


def _check_plan(
    campaigns: list[dict[str, Any]], want: list[tuple[str, int, str]], what: str
) -> list[str]:
    got = [row for c in campaigns for row in realized(c)]
    if got != want:
        return [f"{what}: the trials run ({len(got)}) are not the realized order ({len(want)})"]
    return []


def _layer_ids(layer: str) -> list[str]:
    cells = _cells()
    return [c["id"] for c in cells["layers"]["L0-fixed" if layer == "L0-raw" else layer]]


# --- A1-A6 ------------------------------------------------------------------------------------


def a1(by_seed: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    """L0-fixed passes 100% of G at 5 repetitions, seeds 43 and 44, both settings, N = 1."""
    problems: list[str] = []
    gating = _gating()
    ids = _layer_ids("L0-fixed")
    table = {}
    for seed in (43, 44):
        campaigns = by_seed.get(seed) or []
        if not campaigns:
            problems.append(f"no seed-{seed} campaign")
            continue
        for c in campaigns:
            problems += campaign_problems(c)
            if c["manifest"]["vm"]["concurrency"] != 1:
                problems.append(f"job {c['job']}: A1 runs at N = 1")
        plan = order.plan(ids, seed, 5, list(SETTINGS), acceptance=True)
        problems += _check_plan(campaigns, expected(plan), f"A1 seed {seed}")
        status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
        table[seed] = status
        failing = sorted(cell for cell in gating if status.get(cell) != "PASS")
        if failing:
            problems.append(f"seed {seed}: gating entries not PASS: {failing}")
    return _verdict(problems, {"entries": table})


def a2(by_layer: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Each Stage-1 harness passes its gating and declared cells, 5 repetitions, both settings."""
    problems: list[str] = []
    cells = _cells()
    table = {}
    for layer in ("H-OSW-fixed", "H-GA"):
        campaigns = by_layer.get(layer) or []
        if not campaigns:
            problems.append(f"no {layer} campaign")
            continue
        for c in campaigns:
            problems += campaign_problems(c)
        plan = order.plan(_layer_ids(layer), 43, 5, list(SETTINGS), acceptance=True)
        problems += _check_plan(campaigns, expected(plan), f"A2 {layer}")
        status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
        table[layer] = status
        scored = [c["id"] for c in cells["layers"][layer] if c["status"] in ("gating", "declared")]
        failing = sorted(cell for cell in scored if status.get(cell) != "PASS")
        if failing:
            problems.append(f"{layer}: in-spec cells not PASS: {failing}")
    return _verdict(problems, {"cells": table})


def a3(by_layer: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """30 stress entries, 60 repetitions (30 per setting), zero failures, on each layer."""
    problems: list[str] = []
    table = {}
    for layer in ("L0-fixed", "H-OSW-fixed", "H-GA"):
        campaigns = by_layer.get(layer) or []
        if not campaigns:
            problems.append(f"no {layer} campaign")
            continue
        for c in campaigns:
            problems += campaign_problems(c)
        ids = [i for i in _layer_ids(layer) if i in order.STRESS_ENTRIES]
        plan = order.plan(ids, 43, 30, list(SETTINGS), acceptance=True)
        problems += _check_plan(campaigns, expected(plan), f"A3 {layer}")
        status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
        table[layer] = status
        failing = sorted(cell for cell, s in status.items() if s != "PASS")
        if failing:
            problems.append(f"{layer}: stress entries with a failure: {failing}")
    return _verdict(problems, {"entries": table})


def a4(campaigns: list[dict[str, Any]], n_star: int) -> dict[str, Any]:
    """The volume plan, zero failures, over the N* VMs; its session slices tile the plan."""
    from harness.q2.action_path import volume

    problems: list[str] = []
    plan_data = json.loads(VOLUME_PLAN.read_text(encoding="utf-8"))
    realized_sessions = volume.sessions(plan_data, 43)
    full = [
        {"setting": setting, "trials": list(enumerate(chunk))}
        for setting in SETTINGS
        for chunk in realized_sessions[setting]
    ]
    for c in campaigns:
        problems += campaign_problems(c)
        if c["manifest"]["vm"]["concurrency"] != n_star:
            problems.append(f"job {c['job']}: A4 runs at N* = {n_star}")
    ordered = sorted(
        campaigns, key=lambda c: (c["manifest"]["workload"].get("session_range") or [0])[0]
    )
    spans = [c["manifest"]["workload"].get("session_range") or [0, len(full)] for c in ordered]
    if [s[0] for s in spans[1:]] != [s[1] for s in spans[:-1]] or (
        spans and (spans[0][0] != 0 or spans[-1][1] != len(full))
    ):
        problems.append(f"A4 session ranges {spans} do not tile [0, {len(full)})")
    problems += _check_plan(ordered, expected(full), "A4")
    flags = [t["pass"] for c in campaigns for s in c["sessions"] for t in s["trials"]]
    failed = [
        (s["setting"], t["seq"], t["cell"])
        for c in campaigns
        for s in c["sessions"]
        for t in s["trials"]
        if not t["pass"]
    ]
    if failed:
        problems.append(f"A4: {len(failed)} failed trials, first {failed[:5]}")
    return _verdict(
        problems,
        {
            "trials": len(flags),
            "failures": len(failed),
            "class_actions": plan_data["class_actions"],
            "class_upper_bound_family_95": plan_data["class_upper_bound_family_95"],
            "boot_upper_bound_family_95": plan_data["boot_upper_bound_family_95"],
        },
    )


def a5(boot_reset: dict[str, Any] | None, acceptance: list[dict[str, Any]], sha: str) -> dict:
    """20 of 20 pristine reset checks at the frozen SHA; every acceptance receipt clean."""
    problems: list[str] = []
    if boot_reset is None:
        problems.append("no boot-reset campaign")
    else:
        problems += campaign_problems(boot_reset)
        summary = boot_reset["receipt"].get("summary") or {}
        if boot_reset["manifest"].get("git_sha") != sha:
            problems.append("the boot-reset campaign did not run at the frozen executor SHA")
        if summary.get("sentinel_reset_checks", 0) < 20 or summary.get(
            "sentinel_pristine"
        ) != summary.get("sentinel_reset_checks"):
            problems.append(
                f"reset sentinel {summary.get('sentinel_pristine')} pristine of "
                f"{summary.get('sentinel_reset_checks')} checks (20 of 20 required)"
            )
    for c in acceptance:
        receipt = c["receipt"]
        if receipt.get("qcow2_unchanged") is not True:
            problems.append(f"job {c['job']}: System.qcow2 changed")
        if receipt.get("labelled_containers_left") or (receipt.get("summary") or {}).get(
            "leaked_volumes"
        ):
            problems.append(f"job {c['job']}: leaked labelled containers or volumes")
    return _verdict(problems, {})


def a6(campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    """Every canary app and entry, 5 repetitions, screenshot setting: 100%."""
    problems: list[str] = []
    cells = _cells()
    from harness.q2.vm.manifest import CANARY_APPS

    # The driver's order: the apps as A6's manifest lists them, then each app's entries.
    apps = cells["canary"]["apps"]
    pairs = [f"{app}:{entry}" for app in CANARY_APPS for entry in apps[app]["entries"]]
    for c in campaigns:
        problems += campaign_problems(c)
    plan = order.plan(pairs, 43, 5, ["screenshot"], acceptance=True)
    problems += _check_plan(campaigns, expected(plan), "A6")
    status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
    failing = sorted(cell for cell, s in status.items() if s != "PASS")
    if failing:
        problems.append(f"canary entries not PASS: {failing}")
    return _verdict(problems, {"entries": status})


# --- C1-C4 ------------------------------------------------------------------------------------


def c1(by_layer: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """The detection controls fail their known-defect cells in 5 of 5 repetitions."""
    problems: list[str] = []
    table = {}
    for layer, must_fail in C1_MUST_FAIL.items():
        campaigns = by_layer.get(layer) or []
        if not campaigns:
            problems.append(f"no {layer} campaign")
            continue
        for c in campaigns:
            problems += campaign_problems(c)
        plan = order.plan(_layer_ids(layer), 42, 5, ["screenshot"])
        problems += _check_plan(campaigns, expected(plan), f"C1 {layer}")
        found = outcomes(campaigns)
        table[layer] = {cell: entry_status(v) for cell, v in found.items()}
        for cell in must_fail:
            flags = (found.get(cell) or {}).get("screenshot") or []
            if len(flags) != 5 or any(flags):
                problems.append(f"{layer} {cell}: {sum(flags)} of {len(flags)} passed (0 of 5)")
    return _verdict(problems, {"cells": table})


def c2(campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    """L0-raw fails exactly the predicted set (an entry fails unless PASS 5 of 5)."""
    import yaml

    problems: list[str] = []
    predicted = set(yaml.safe_load(PREDICTION.read_text(encoding="utf-8"))["predicted_fail"])
    for c in campaigns:
        problems += campaign_problems(c)
    plan = order.plan(_layer_ids("L0-raw"), 42, 5, ["screenshot"])
    problems += _check_plan(campaigns, expected(plan), "C2")
    status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
    observed = {cell for cell, s in status.items() if s != "PASS"}
    if observed != predicted:
        problems.append(
            f"L0-raw failing set deviates: unpredicted failures {sorted(observed - predicted)}, "
            f"predicted but passing {sorted(predicted - observed)}"
        )
    return _verdict(problems, {"entries": status, "predicted_fail": sorted(predicted)})


def _signature(campaigns: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Per cell: the device events without timestamps, the text buffer and the terminal."""
    out: dict[str, list[Any]] = {}
    for c in campaigns:
        for session in c["sessions"]:
            for trial in session["trials"]:
                out.setdefault(trial["cell"], []).append(
                    [trial["events"], trial["text"], trial["terminal"]]
                )
    return out


def c3(
    mutants: dict[tuple[str, str], list[dict[str, Any]]],
    references: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Every scored, non-equivalent mutant is killed by a cell of its layer that can kill."""
    import yaml

    from harness.q2.action_path import mutants as kit

    problems: list[str] = []
    operators = yaml.safe_load(OPERATORS.read_text(encoding="utf-8"))
    cells = _cells()
    table = {}
    for operator, layer in kit.scored_pairs(operators):
        campaigns = mutants.get((operator, layer)) or []
        if not campaigns:
            problems.append(f"{operator} on {layer}: no run")
            continue
        for c in campaigns:
            problems += campaign_problems(c)
        plan = order.plan(_layer_ids(layer), 42, 1, ["screenshot"])
        problems += _check_plan(campaigns, expected(plan), f"C3 {operator} {layer}")
        can_kill = {
            c["id"]
            for c in cells["layers"][layer]
            if layer == "L0-fixed" or c["status"] in ("gating", "declared")
        }
        status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
        killers = sorted(cell for cell, s in status.items() if s != "PASS" and cell in can_kill)
        if killers:
            table[f"{operator} {layer}"] = {"outcome": "killed", "killers": killers}
            continue
        reference = references.get(layer) or []
        if reference and _signature(campaigns) == _signature(reference):
            table[f"{operator} {layer}"] = {"outcome": "equivalent", "killers": []}
        else:
            table[f"{operator} {layer}"] = {"outcome": "survived", "killers": []}
            problems.append(f"{operator} on {layer} survived and is not equivalent")
    for campaigns in references.values():
        for c in campaigns:
            problems += campaign_problems(c)
    return _verdict(problems, {"mutants": table})


def c4(a1_campaigns: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """In every A1 trial of an entry with an R-dev reference, the projection matches."""
    problems: list[str] = []
    checked = 0
    for c in a1_campaigns:
        for session in c["sessions"]:
            for trial in session["trials"]:
                if trial["c4"] is None:
                    continue
                checked += 1
                if trial["c4"] is not True:
                    problems.append(f"job {c['job']} {session['setting']} {trial['cell']}")
    return _verdict(problems, {"trials_checked": checked})


# --- concurrency ------------------------------------------------------------------------------


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(q * len(ordered))) - 1]


def foreign_abort(campaign: dict[str, Any]) -> list[str]:
    """Section 9: a foreign Slurm job started, or foreign jobs held more than 8 CPUs."""
    own = campaign["job"]
    snapshots = [s for session in campaign["sessions"] for s in session["snapshots"] if s]
    snapshots.sort(key=lambda s: s.get("t") or 0)

    def running(snapshot: dict[str, Any]) -> dict[str, int]:
        rows = snapshot.get("squeue_foreign") or []
        out = {}
        for row in rows:
            if len(row) >= 4 and row[0] != own and row[2] == "RUNNING":
                out[row[0]] = int(row[3]) if str(row[3]).isdigit() else 0
        return out

    if not snapshots:
        return ["no host snapshots"]
    first = set(running(snapshots[0]))
    reasons = []
    for snapshot in snapshots:
        now = running(snapshot)
        started = sorted(set(now) - first)
        if started:
            reasons.append(f"foreign job started: {started}")
        if sum(now.values()) > FOREIGN_CPUS_MAX:
            reasons.append(f"foreign jobs hold {sum(now.values())} CPUs")
    return sorted(set(reasons))


def rung(campaigns: list[dict[str, Any]], step_p95_n1: float) -> dict[str, Any]:
    """Whether one ladder rung qualifies (section 9), with its measurements."""
    from harness.q2.vm.manifest import ladder_reps

    problems: list[str] = []
    n = campaigns[0]["manifest"]["vm"]["concurrency"]
    for c in campaigns:
        problems += campaign_problems(c)
        if c["manifest"]["vm"]["concurrency"] != n:
            problems.append("a rung's campaigns run at one concurrency")
    aborts = sorted({r for c in campaigns for r in foreign_abort(c)})
    plan = order.plan(_layer_ids("L0-fixed"), 43, ladder_reps(n), list(SETTINGS), acceptance=True)
    problems += _check_plan(campaigns, expected(plan), f"rung N={n}")
    boots = [s["boot_s"] for c in campaigns for s in c["sessions"] if s["boot_s"] is not None]
    steps = [x for c in campaigns for s in c["sessions"] for t in s["trials"] for x in t["steps_s"]]
    boot_p95, step_p95 = quantile(boots, 0.95), quantile(steps, 0.95)
    if len(boots) < MIN_RUNG_BOOTS:
        problems.append(f"{len(boots)} cold boots measured (at least {MIN_RUNG_BOOTS})")
    if boot_p95 is None or boot_p95 > BOOT_P95_MAX_S:
        problems.append(f"boot p95 {boot_p95} s > {BOOT_P95_MAX_S} s")
    if step_p95 is None or step_p95 > STEP_P95_FACTOR * step_p95_n1:
        problems.append(f"step p95 {step_p95} s > {STEP_P95_FACTOR} x {step_p95_n1} s")
    gating = _gating()
    status = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
    failing = sorted(cell for cell in gating if status.get(cell) != "PASS")
    if failing:
        problems.append(f"gating entries not PASS: {failing}")
    return {
        "n": n,
        "aborted": bool(aborts),
        "abort_reasons": aborts,
        "qualifies": not problems and not aborts,
        "problems": problems,
        "boots": len(boots),
        "boot_p95_s": boot_p95,
        "step_p95_s": step_p95,
    }


def n_star(a1_campaigns: list[dict[str, Any]], rungs: dict[int, list[dict[str, Any]]]) -> dict:
    """N*: the largest rung that qualifies; 1 when none does (A1 gates N = 1 itself)."""
    steps = [
        x for c in a1_campaigns for s in c["sessions"] for t in s["trials"] for x in t["steps_s"]
    ]
    reference = quantile(steps, 0.95)
    results = {}
    best = 1
    for n in LADDER_RUNGS:
        if n not in rungs:
            continue
        results[n] = rung(rungs[n], reference or 0.0)
        if results[n]["qualifies"]:
            best = max(best, n)
    return {
        "n_star": best,
        "step_p95_n1_s": reference,
        "rungs": results,
        "program_kill_criterion": best < 40,
    }
