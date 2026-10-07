"""Acceptance analysis of q2-action-path-v1: A1-A6, C1-C4 and the concurrency N*.

This module restates the preregistration's decision rules (sections 5-9 of
``program/preregistrations/q2-action-path-v1.md``) as code, frozen with the inputs
addendum (and pinned again by the executor addendum) before any scored campaign runs,
C2 included, so the verdicts are computed the way the text says and nothing is chosen
after the data. It reads campaign run directories as the VM lane writes them
(``manifest.json``, ``receipt.json``, ``preflight.txt``, ``cycles/cycle-NN.json``,
``cycles/record-NN.json``).

Rules that apply to every criterion:

* a campaign counts only if it ended COMPLETED with exit code 0:0, its receipt's
  ``infra_gates_pass`` is true, ``System.qcow2`` is unchanged and no labelled container
  or volume was left (sections 6.1 and 7, A5). The end state is read from the batch
  script's own last record (``driver_exit=0 labelled_containers_left=0`` in
  ``preflight.txt``, written just before it exits 0; a job killed by a signal, a time
  limit or a node failure never writes it), and from Slurm when the operator read it in
  time, in which case both must agree;
* a trial is PASS only as ``verdict.judge`` judged it, infrastructure failures
  included (section 6.1); a session whose ``DesktopEnv.reset`` observation was not
  delivered charges its first trial (``reset_observation``); an entry is PASS only at k
  of k repetitions, and an entry that is PASS in one observation setting and not the
  other fails (section 5);
* reruns (section 6.1): a campaign may be rerun once, as a new attempt with a new
  output path, and only when the earlier attempt did not count (a ladder rung also when
  it aborted on foreign load); every trial of every attempt is reported, and a failed
  trial in an earlier attempt counts against the criterion (an aborted rung's do not);
* the trials a criterion runs must be exactly the realized order its manifest
  declares (``order.plan`` or ``volume.sessions``), so a campaign cut short cannot pass,
  and every campaign of a criterion runs one source tree (git SHA, tree digest and
  repair attempt).

Standard library plus the suite's own modules; Python 3.10 compatible.
"""

from __future__ import annotations

import glob
import json
import math
import os
import re
from collections.abc import Callable, Iterable
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
MAX_ATTEMPTS = 2  # section 6.1: a campaign runs at most twice (one rerun)
BATCH_END = re.compile(r"^driver_exit=(\d+) labelled_containers_left=(\d+)$", re.M)
# Section 8, C2 (design decision 34): an L0-raw trial is judged on the event and text
# channels. The marker (section 5, condition 3) is reported, not judged, and an R-dev
# projection is compared without the modifier state of key releases.
C2_EXCUSED = ("marker ",)
C2_RDEV = "R-dev projection differs"
STATE_BITS = (("Shift", 1), ("Control", 4), ("Mod1", 8), ("Mod4", 64))


# --- loading ----------------------------------------------------------------------------------


def _read(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def batch_end(run_dir: str) -> dict[str, int] | None:
    """The batch script's own last record, or None when it never reached its end."""
    path = os.path.join(run_dir, "preflight.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        found = BATCH_END.findall(handle.read())
    if not found:
        return None
    driver_exit, left = found[-1]
    return {"driver_exit": int(driver_exit), "labelled_containers_left": int(left)}


def recorded_slurm_state(run_dir: str, job: str) -> dict[str, str] | None:
    """The end state ``scripts/record_slurm_end_states.sh`` caught for this job, if any.

    The watcher writes ``<run root>/slurm-state/<job>.txt`` (the ``scontrol show job``
    text) next to the job's run directory; a job Slurm had already forgotten is recorded
    as ``forgotten`` and gives None.
    """
    path = os.path.join(os.path.dirname(os.path.normpath(run_dir)), "slurm-state", f"{job}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    state = re.search(r"\bJobState=(\S+)", text)
    code = re.search(r"\bExitCode=(\S+)", text)
    if not state or not code:
        return None
    return {"state": state.group(1), "exit_code": code.group(1)}


def load(
    run_dir: str,
    slurm: dict[str, str] | None = None,
    earlier: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One campaign: manifest, receipt, end state and its sessions' trials.

    ``slurm`` is the job's Slurm end state (``{"state", "exit_code"}``) when the operator
    read it with ``scontrol show job`` before Slurm forgot the job; when it is not given,
    the watcher's record is used if there is one, and without either the batch script's
    own record decides. ``earlier`` holds the loaded earlier attempts of the same
    campaign (section 6.1), oldest first.
    """
    manifest = _read(os.path.join(run_dir, "manifest.json"))
    receipt = _read(os.path.join(run_dir, "receipt.json"))
    if slurm is None:
        slurm = recorded_slurm_state(run_dir, str(receipt.get("job_id")))
    sessions = []
    paths = glob.glob(os.path.join(run_dir, "cycles", "cycle-[0-9][0-9]*.json"))
    # Cycle numbers are plan indices; sort them as numbers (cycle-100 after cycle-99).
    for path in sorted(paths, key=lambda p: int(os.path.basename(p)[6:-5])):
        cycle = _read(path)
        record_path = path.replace("cycle-", "record-")
        record = _read(record_path) if os.path.exists(record_path) else {}
        trials = [_trial(t, cycle.get("setting")) for t in cycle.get("trials") or []]
        reset = reset_observation(cycle.get("reset_observation"), cycle.get("setting"))
        if reset is not None and not reset["delivered"] and trials:
            # Section 6.1: a reset observation DesktopEnv's retries did not deliver is an
            # infrastructure failure of the boot, charged to the session's first trial.
            trials[0]["pass"] = False
            trials[0]["infra"] = sorted({*trials[0]["infra"], "reset_observation"})
        sessions.append(
            {
                "cycle": cycle.get("cycle"),
                "setting": cycle.get("setting"),
                "boot_s": (cycle.get("boot") or {}).get("t_screenshot_200"),
                "error": cycle.get("error"),
                "reset_observation": reset,
                "trials": trials,
                "snapshots": [record.get("host_before"), record.get("host_after")],
            }
        )
    return {
        "job": str(receipt.get("job_id")),
        "run_dir": run_dir,
        "manifest": manifest,
        "receipt": receipt,
        "slurm": slurm,
        "batch": batch_end(run_dir),
        "sessions": sessions,
        "earlier": list(earlier or []),
    }


def reset_observation(raw: dict[str, Any] | None, setting: str | None) -> dict[str, Any] | None:
    """Whether ``DesktopEnv.reset``'s observation was delivered, and which parts retried."""
    if not raw:
        return None

    def delivered(attempts: list[dict[str, Any]], flag: Any) -> bool:
        if isinstance(flag, bool):
            return flag
        # Older records carry only the attempts: delivered when the last one answered 200.
        return bool(attempts) and attempts[-1].get("status") == 200

    shots = raw.get("screenshot_attempts") or []
    ok = delivered(shots, raw.get("screenshot_ok"))
    retried = ["screenshot"] if ok and len(shots) > 1 else []
    if setting == "screenshot+a11y":
        trees = raw.get("accessibility_attempts") or []
        tree_ok = delivered(trees, raw.get("accessibility_ok"))
        ok = ok and tree_ok
        if tree_ok and len(trees) > 1:
            retried.append("accessibility")
    return {"delivered": ok, "retried": retried}


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
        "reasons": verdict.get("reasons"),
        "c4": raw.get("c4"),
        "events": [r[:-1] for r in raw.get("tap_window") or [] if _device(r)],
        "probe_events": end.get("events") if end.get("ok") else None,
        "text": end.get("text"),
        "terminal": raw.get("terminal"),
        "steps_s": [s for s in steps if isinstance(s, int | float)],
    }


def _device(record: list[Any]) -> bool:
    return bool(record) and record[0] in (
        "KeyPress", "KeyRelease", "ButtonPress", "ButtonRelease", "MotionNotify",
    )  # fmt: skip


# --- shared rules -----------------------------------------------------------------------------


def end_state_problems(campaign: dict[str, Any]) -> list[str]:
    """Whether the job ended COMPLETED with exit code 0:0 (section 6.1)."""
    out = []
    job = campaign["job"]
    slurm = campaign.get("slurm")
    batch = campaign.get("batch")
    if slurm is not None and (slurm.get("state") != "COMPLETED" or slurm.get("exit_code") != "0:0"):
        out.append(f"job {job}: Slurm {slurm.get('state')} {slurm.get('exit_code')}")
    if batch is None:
        if slurm is None:
            out.append(f"job {job}: end state unknown (no batch record and no Slurm state)")
        else:
            out.append(f"job {job}: the batch script never recorded its end")
    elif batch.get("driver_exit") != 0 or batch.get("labelled_containers_left") != 0:
        out.append(
            f"job {job}: batch script ended with driver_exit={batch.get('driver_exit')} "
            f"labelled_containers_left={batch.get('labelled_containers_left')}"
        )
    return out


def counting_problems(campaign: dict[str, Any]) -> list[str]:
    """Why this attempt cannot count at all, ignoring its earlier attempts (empty = it can)."""
    out = end_state_problems(campaign)
    receipt = campaign["receipt"]
    summary = receipt.get("summary") or {}
    if summary.get("infra_gates_pass") is not True:
        out.append(f"job {campaign['job']}: infra_gates_pass is not true")
    if receipt.get("qcow2_unchanged") is not True:
        out.append(f"job {campaign['job']}: System.qcow2 changed or unchecked")
    if receipt.get("labelled_containers_left") or summary.get("leaked_volumes"):
        out.append(f"job {campaign['job']}: labelled containers or volumes left")
    return out


def failed_trials(campaign: dict[str, Any]) -> list[tuple[str, int, str]]:
    return [
        (session["setting"], trial["seq"], trial["cell"])
        for session in campaign["sessions"]
        for trial in session["trials"]
        if not trial["pass"]
    ]


def campaign_problems(
    campaign: dict[str, Any],
    rerun_allowed: Callable[[dict[str, Any]], bool] | None = None,
    earlier_failures_count: Callable[[dict[str, Any]], bool] | None = None,
) -> list[str]:
    """Why a campaign cannot count at all (empty when it can), its reruns included.

    Section 6.1: at most ``MAX_ATTEMPTS`` attempts; an earlier attempt may be rerun only
    when it did not count (``rerun_allowed``; the ladder also admits a foreign-load
    abort), and its failed trials count against the criterion unless
    ``earlier_failures_count`` says otherwise (an aborted rung's do not).
    """
    rerun_allowed = rerun_allowed or (lambda prev: bool(counting_problems(prev)))
    earlier_failures_count = earlier_failures_count or (lambda prev: True)
    out = counting_problems(campaign)
    earlier = campaign.get("earlier") or []
    if len(earlier) + 1 > MAX_ATTEMPTS:
        out.append(f"job {campaign['job']}: {len(earlier) + 1} attempts (at most {MAX_ATTEMPTS})")
    for previous in earlier:
        if not rerun_allowed(previous):
            out.append(
                f"job {campaign['job']}: earlier attempt {previous['job']} counted and was rerun"
            )
        failed = failed_trials(previous)
        if failed and earlier_failures_count(previous):
            out.append(
                f"job {campaign['job']}: earlier attempt {previous['job']} has "
                f"{len(failed)} failed trials, first {failed[:3]}"
            )
    return out


def version_problems(campaigns: list[dict[str, Any]], what: str) -> list[str]:
    """Every campaign of one criterion runs one source tree and one repair attempt."""
    versions = {
        (
            c["manifest"].get("git_sha"),
            (c["manifest"].get("source") or {}).get("tree_sha256"),
            (c["manifest"].get("workload") or {}).get("attempt"),
        )
        for c in campaigns
    }
    if len(versions) > 1:
        return [f"{what}: campaigns ran {len(versions)} different source trees or attempts"]
    return []


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
    out = version_problems(campaigns, what)
    got = [row for c in campaigns for row in realized(c)]
    if got != want:
        out.append(f"{what}: the trials run ({len(got)}) are not the realized order ({len(want)})")
    return out


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


def _keysym_name(value: Any) -> str:
    from harness.q2.action_path.ir import CANONICAL_NAME

    return CANONICAL_NAME.get(int(value or 0), f"0x{int(value or 0):x}")


def _states(state: Any) -> list[str]:
    return [name for name, bit in STATE_BITS if int(state or 0) & bit]


def c2_projection(trial: dict[str, Any], cell: dict[str, Any]) -> list[list[Any]] | None:
    """The trial's R-dev projection with the modifier state of key releases left out.

    The channel is the one ``verdict.judge`` reads: the probe's event log for ``observable:
    app`` cells (``[kind, keycode, state, x, y, time, keysym0, ...]``), the XRecord window for
    ``raw-only`` cells (``[kind, keycode, state, keysym0]`` once the timestamp is dropped).
    """
    if cell.get("observable", "app") == "app":
        records = trial.get("probe_events")
        keysym_at = 6
    else:
        records = trial.get("events")
        keysym_at = 3
    if records is None:
        return None
    out: list[list[Any]] = []
    for record in records:
        kind = record[0]
        if kind not in ("KeyPress", "KeyRelease"):
            continue
        keysym = _keysym_name(record[keysym_at] if len(record) > keysym_at else 0)
        out.append([kind, keysym] if kind == "KeyRelease" else [kind, keysym, _states(record[2])])
    return out


def c2_reference(cell: dict[str, Any]) -> list[list[Any]] | None:
    events = (cell.get("expect") or {}).get("events")
    if (cell.get("expect") or {}).get("oracle") != "rdev" or events is None:
        return None
    return [[e[0], e[1]] if e[0] == "KeyRelease" else [e[0], e[1], list(e[2])] for e in events]


def c2_trial_pass(trial: dict[str, Any], cell: dict[str, Any]) -> bool:
    """C2's reading of one L0-raw trial (section 8, design decision 34).

    PASS under section 5 is PASS here. Otherwise the trial passes only when it has no
    infrastructure failure and every reason it failed is excused: a marker reason
    (condition 3 is reported, not judged, for L0-raw), or an R-dev projection difference
    that disappears when key releases are compared without their modifier state.
    """
    if trial["pass"]:
        return True
    if trial.get("infra") or trial.get("reasons") is None:
        return False
    remaining = [r for r in trial["reasons"] if not r.startswith(C2_EXCUSED)]
    if any(r.startswith(C2_RDEV) for r in remaining):
        reference = c2_reference(cell)
        if reference is not None and c2_projection(trial, cell) == reference:
            remaining = [r for r in remaining if not r.startswith(C2_RDEV)]
    return not remaining


def c2(campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    """L0-raw fails exactly the predicted set (an entry fails unless PASS 5 of 5).

    Each trial is read by ``c2_trial_pass``; the section-5 verdicts (marker included) are
    reported next to it as ``strict_entries``.
    """
    import yaml

    problems: list[str] = []
    predicted = set(yaml.safe_load(PREDICTION.read_text(encoding="utf-8"))["predicted_fail"])
    cells = {c["id"]: c for c in _cells()["layers"]["L0-fixed"]}
    for c in campaigns:
        problems += campaign_problems(c)
    plan = order.plan(_layer_ids("L0-raw"), 42, 5, ["screenshot"])
    problems += _check_plan(campaigns, expected(plan), "C2")
    flags: dict[str, dict[str, list[bool]]] = {}
    for c in campaigns:
        for session in c["sessions"]:
            for trial in session["trials"]:
                flags.setdefault(trial["cell"], {}).setdefault(session["setting"], []).append(
                    c2_trial_pass(trial, cells[trial["cell"]])
                )
    status = {cell: entry_status(v) for cell, v in flags.items()}
    strict = {cell: entry_status(v) for cell, v in outcomes(campaigns).items()}
    observed = {cell for cell, s in status.items() if s != "PASS"}
    if observed != predicted:
        problems.append(
            f"L0-raw failing set deviates: unpredicted failures {sorted(observed - predicted)}, "
            f"predicted but passing {sorted(predicted - observed)}"
        )
    return _verdict(
        problems,
        {"entries": status, "strict_entries": strict, "predicted_fail": sorted(predicted)},
    )


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


def _cell_results(campaigns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per cell: its status over the repetitions and whether any trial had an infra failure."""
    out: dict[str, dict[str, Any]] = {}
    for cell, flags in outcomes(campaigns).items():
        out[cell] = {"status": entry_status(flags), "infra": False}
    for c in campaigns:
        for session in c["sessions"]:
            for trial in session["trials"]:
                if trial["infra"]:
                    out[trial["cell"]]["infra"] = True
    return out


def c3(
    mutants: dict[tuple[str, str], list[dict[str, Any]]],
    references: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Every scored, non-equivalent mutant is killed by a cell of its layer that can kill.

    A cell kills a mutant only when the mutant's run fails it without an infrastructure
    failure and the unmutated reference run passed it cleanly (section 8). A failing cell
    with an infrastructure failure never kills; it is reported under ``infra_cells``, and a
    mutant with no clean kill is equivalent (byte-identical signature on every cell) or
    survives.
    """
    import yaml

    from harness.q2.action_path import mutants as kit

    problems: list[str] = []
    operators = yaml.safe_load(OPERATORS.read_text(encoding="utf-8"))
    predicted_cells = {
        (op["id"], layer): list(spec.get("kill_cells") or [])
        for op in operators["operators"]
        for layer, spec in (op.get("applies") or {}).items()
    }
    cells = _cells()
    for layer in C3_LAYERS:
        if not references.get(layer):
            problems.append(f"no unmutated reference run on {layer}")
    for campaigns in references.values():
        for c in campaigns:
            problems += campaign_problems(c)
    for layer, campaigns in references.items():
        plan = order.plan(_layer_ids(layer), 42, 1, ["screenshot"])
        problems += _check_plan(campaigns, expected(plan), f"C3 reference {layer}")
    reference_results = {layer: _cell_results(c) for layer, c in references.items()}
    table = {}
    for operator, layer in kit.scored_pairs(operators):
        key = f"{operator} {layer}"
        campaigns = mutants.get((operator, layer)) or []
        if not campaigns:
            problems.append(f"{operator} on {layer}: no run")
            continue
        for c in campaigns:
            problems += campaign_problems(c)
        plan = order.plan(_layer_ids(layer), 42, 1, ["screenshot"])
        problems += _check_plan(campaigns, expected(plan), f"C3 {operator} {layer}")
        problems += version_problems(
            campaigns + (references.get(layer) or []), f"C3 {operator} {layer} and its reference"
        )
        can_kill = {
            c["id"]
            for c in cells["layers"][layer]
            if layer == "L0-fixed" or c["status"] in ("gating", "declared")
        }
        reference = reference_results.get(layer) or {}
        killers, infra_cells, reference_not_clean = [], [], []
        for cell, result in sorted(_cell_results(campaigns).items()):
            if result["status"] == "PASS" or cell not in can_kill:
                continue
            if result["infra"]:
                infra_cells.append(cell)
                continue
            ref = reference.get(cell)
            if ref is None or ref["status"] != "PASS" or ref["infra"]:
                reference_not_clean.append(cell)
                continue
            killers.append(cell)
        entry = {
            "killers": killers,
            "predicted_killers": predicted_cells.get((operator, layer), []),
            "infra_cells": infra_cells,
            "reference_not_clean": reference_not_clean,
        }
        if killers:
            entry["outcome"] = "killed"
        elif references.get(layer) and _signature(campaigns) == _signature(references[layer]):
            entry["outcome"] = "equivalent"
        else:
            entry["outcome"] = "survived"
            problems.append(f"{operator} on {layer} survived and is not equivalent")
        table[key] = entry
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

    def rerun_allowed(previous: dict[str, Any]) -> bool:
        # Section 9: an aborted rung (or one that did not count) is rerun once.
        return bool(counting_problems(previous)) or bool(foreign_abort(previous))

    earlier = []
    for c in campaigns:
        problems += campaign_problems(
            c, rerun_allowed, earlier_failures_count=lambda prev: not foreign_abort(prev)
        )
        if c["manifest"]["vm"]["concurrency"] != n:
            problems.append("a rung's campaigns run at one concurrency")
        for previous in c.get("earlier") or []:
            earlier.append(
                {
                    "job": previous["job"],
                    "abort_reasons": foreign_abort(previous),
                    "failed_trials": len(failed_trials(previous)),
                }
            )
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
        "earlier_attempts": earlier,
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
