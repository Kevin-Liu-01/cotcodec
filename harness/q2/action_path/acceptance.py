"""Acceptance analysis of q2-action-path-v1: A1-A7, C1-C4 and the concurrency N*.

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
  delivered charges its first trial (``reset_observation``, an infrastructure type and a
  reason of that trial); an entry is PASS only at k of k repetitions, and an entry that
  is PASS in one observation setting and not the other fails (section 5). One exception
  (decisions D30 and D33): in A1-A4 and the concurrency ladder a trial whose only
  failure is a guest-server restart during an observation call, with the tree it left
  undelivered, is excused: reported and not counted (``restart_only``). A1-A3 judge an
  entry on its counted repetitions and fail it on a second excused trial in that entry,
  over both observation settings and every attempt (A1: both seeds; ``RESTART_LIMIT``);
  a ladder rung with more than two excused trials does not qualify; A4 has no such
  limit;
* the observation service has its own bound (A7, decision D30): guest-server restarts
  per ``/accessibility`` call, judged on the exact one-sided 95% Poisson upper bound,
  with the restarts of every attempt and the calls of the counting attempts only, capped
  at the plan's 39,036 calls (decision D33);
* reruns (section 6.1): a campaign may be rerun once, as a new attempt with a new
  output path, and only when the earlier attempt did not count (a ladder rung also when
  it aborted on foreign load or lacks host snapshots); every trial of every attempt is
  reported, and a failed trial in an earlier attempt counts against the criterion
  exactly as if that attempt had counted: on the cells the criterion judges, less the
  trials it excuses (only a rung aborted on foreign load has none that count; a rung
  attempt without host snapshots is not an abort); excused trials count toward A1-A3's
  and the ladder's limits over every attempt, so a rerun never resets them; C1-C3 judge
  an earlier attempt's trials by their own rules (C1: a known-defect cell must fail in
  every attempt; C2: an earlier failure counts outside the predicted set only; C3: kills
  and equivalence from the counting attempt, while a cell the reference did not pass
  cleanly in any attempt cannot kill);
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
from harness.q2.vm import suite

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
# Decisions D30 and D33. A1-A4 and the ladder do not count a trial whose only failure is a
# guest-server restart (with the accessibility tree that restart left undelivered); A7
# bounds the restarts per /accessibility call at OBSERVATION_BOUND, judged on the exact
# one-sided upper bound at level 1 - OBSERVATION_ALPHA. The development rate (one restart
# in 8,114 calls, runs 484-622) is reported with A4 and A7 with its exact two-sided 95%
# interval.
RESTART = "guest_server_restart"
RESET = "reset_observation"
# The infrastructure types a restart excuses: a restart during the entry excuses itself
# and the tree it left undelivered; a restart across the session's reset observation
# (``reset_restart``) excuses that observation when its tree alone was not delivered.
RESTART_EXCUSED = (RESTART, "accessibility")
# Decision D33: an A1-A3 entry may lose at most one of its repetitions (both observation
# settings, every attempt; in A1 both seeds) to an excused trial (a second one fails the
# entry: ``RESTART_LIMIT``, never FLAKY), and a ladder rung at most two trials in all (a
# third leaves the rung unqualified).
MAX_EXCUSED_PER_ENTRY = 1
MAX_EXCUSED_PER_RUNG = 2
RESTART_LIMIT = "RESTART_LIMIT"
OBSERVATION_BOUND = 5e-4
OBSERVATION_ALPHA = 0.05
# Section 7, A7: the plan's accessibility calls (516 reset observations and 38,520 step
# observations); A7's n is the counting attempts' calls capped here (decision D33).
OBSERVATION_PLAN_CALLS = 39036
DEVELOPMENT_RESTARTS, DEVELOPMENT_CALLS = 1, 8114


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
            # infrastructure failure of the boot, charged to the session's first trial as
            # an infrastructure type and a reason, like every other one (verdict.judge).
            first = trials[0]
            first["pass"] = False
            first["infra"] = sorted({*first["infra"], RESET})
            if isinstance(first["reasons"], list) and f"infra: {RESET}" not in first["reasons"]:
                first["reasons"] = [*first["reasons"], f"infra: {RESET}"]
            # Decision D30 (design decision 40): only its tree was missing and the server
            # restarted across it, so the restart left it undelivered.
            first["reset_restart"] = reset["failed"] == ["accessibility"] and reset_restart(cycle)
        sessions.append(
            {
                "cycle": cycle.get("cycle"),
                "setting": cycle.get("setting"),
                "boot_s": (cycle.get("boot") or {}).get("t_screenshot_200"),
                "error": cycle.get("error"),
                "reset_observation": reset,
                "trials": trials,
                "snapshots": [record.get("host_before"), record.get("host_after")],
                "restarts": suite.session_restarts(cycle),
                "accessibility_calls": suite.accessibility_calls(cycle),
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
    """Whether ``DesktopEnv.reset``'s observation was delivered, which parts retried and
    which parts were not delivered (``failed``)."""
    if not raw:
        return None

    def delivered(attempts: list[dict[str, Any]], flag: Any) -> bool:
        if isinstance(flag, bool):
            return flag
        # Older records carry only the attempts: delivered when the last one answered 200.
        return bool(attempts) and attempts[-1].get("status") == 200

    shots = raw.get("screenshot_attempts") or []
    shot_ok = delivered(shots, raw.get("screenshot_ok"))
    failed = [] if shot_ok else ["screenshot"]
    retried = ["screenshot"] if shot_ok and len(shots) > 1 else []
    if setting == "screenshot+a11y":
        trees = raw.get("accessibility_attempts") or []
        tree_ok = delivered(trees, raw.get("accessibility_ok"))
        if not tree_ok:
            failed.append("accessibility")
        elif len(trees) > 1:
            retried.append("accessibility")
    return {"delivered": not failed, "retried": retried, "failed": failed}


def reset_restart(cycle: dict[str, Any]) -> bool:
    """Whether the guest server restarted across the session's reset observation.

    The reset observation is taken between the session's start (the baseline check and
    the warm-up, each of whose reports names the server process) and the first trial's
    pre guard; a different server process in that guard's report is a restart in between.
    Both ids must be known: when the pre guard could not run, the restart is the first
    trial's own (``guest_server_restart``, design decision 39) and nothing is excused here.
    """
    start = cycle.get("start") or {}
    ids = [
        report["server_pid"]
        for report in (start.get("baseline_check"), start.get("warmup"))
        if isinstance((report or {}).get("server_pid"), int)
    ]
    trials = cycle.get("trials") or []
    pre = ((trials[0].get("pre") or {}).get("server_pid")) if trials else None
    return bool(ids) and isinstance(pre, int) and pre != ids[-1]


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


def failed_trials(
    campaign: dict[str, Any],
    excused: Callable[[dict[str, Any]], bool] | None = None,
    judged: set[str] | None = None,
) -> list[tuple[str, int, str]]:
    """(setting, seq, cell) of every failed trial, less those ``excused`` (restart-only
    trials, decisions D30 and D33), on the cells in ``judged`` (every cell when None)."""
    return [
        (session["setting"], trial["seq"], trial["cell"])
        for session in campaign["sessions"]
        for trial in session["trials"]
        if not trial["pass"]
        and not (excused and excused(trial))
        and (judged is None or trial["cell"] in judged)
    ]


def restart_only(trial: dict[str, Any]) -> bool:
    """Decisions D30 and D33: a failed trial whose only failure is a guest-server restart.

    Either a restart during the entry (``guest_server_restart``) with, at most, an
    ``/accessibility`` failure (the tree the restart left undelivered), or, for a session's
    first trial, a restart across the reset observation that left only its tree
    undelivered (``reset_restart``), or both. A1-A4 and the ladder report such a trial and
    do not count it (it is excused); any other reason in the same trial (an event, text,
    marker or guard difference, or an infrastructure failure of any other type: an
    ``execute`` or ``guard_script`` failure from a restart during ``/execute`` or a guard,
    or an undelivered reset screenshot) counts as usual. Both the infrastructure types and
    the reasons are checked.
    """
    if trial["pass"]:
        return False
    infra = set(trial.get("infra") or [])
    excused: set[str] = set()
    if RESTART in infra:
        excused.update(RESTART_EXCUSED)
    if trial.get("reset_restart"):
        excused.add(RESET)
    reasons = trial.get("reasons")
    return (
        bool(excused)
        and reasons is not None
        and infra <= excused
        and set(reasons) <= {f"infra: {kind}" for kind in excused}
    )


def campaign_problems(
    campaign: dict[str, Any],
    rerun_allowed: Callable[[dict[str, Any]], bool] | None = None,
    earlier_failures_count: Callable[[dict[str, Any]], bool] | None = None,
    excused: Callable[[dict[str, Any]], bool] | None = None,
    judged: set[str] | None = None,
) -> list[str]:
    """Why a campaign cannot count at all (empty when it can), its reruns included.

    Section 6.1: at most ``MAX_ATTEMPTS`` attempts; an earlier attempt may be rerun only
    when it did not count (``rerun_allowed``; the ladder also admits a foreign-load
    abort), and its failed trials count against the criterion exactly as if it had
    counted: unless ``earlier_failures_count`` says otherwise (an aborted rung's do not),
    the criterion ``excused`` them (restart-only trials in A1-A4 and the ladder, C2's
    reading of an L0-raw trial) or they are on cells the criterion does not judge
    (``judged``: G for A1 and the ladder, the in-spec cells for A2, the cells outside the
    predicted set for C2; every cell when None). Excused trials of every attempt count
    toward A1-A3's and the ladder's limits; those are checked by the criterion. C1 and C3
    read an earlier attempt's trials by their own rules (their cells fail by design).
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
        failed = failed_trials(previous, excused, judged)
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


def outcomes(
    campaigns: Iterable[dict[str, Any]],
    excused: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, dict[str, list[bool]]]:
    """cell -> setting -> pass flags of the counted trials of the campaigns: every trial,
    less those ``excused`` (restart-only trials in A1-A3 and the ladder, decision D33)."""
    out: dict[str, dict[str, list[bool]]] = {}
    for campaign in campaigns:
        for session in campaign["sessions"]:
            for trial in session["trials"]:
                if excused and excused(trial):
                    continue
                out.setdefault(trial["cell"], {}).setdefault(session["setting"], []).append(
                    trial["pass"]
                )
    return out


def every_attempt(campaigns: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every attempt of the campaigns, earlier ones first (section 6.1)."""
    return [a for c in campaigns for a in [*(c.get("earlier") or []), c]]


def excused_trials(
    campaigns: Iterable[dict[str, Any]],
    excused: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, int]:
    """cell -> number of excused (restart-only) trials in the given attempts, over both
    observation settings."""
    excused = excused or restart_only
    out: dict[str, int] = {}
    for campaign in campaigns:
        for session in campaign["sessions"]:
            for trial in session["trials"]:
                if excused(trial):
                    out[trial["cell"]] = out.get(trial["cell"], 0) + 1
    return out


def _excused_total(campaigns: Iterable[dict[str, Any]]) -> int:
    return sum(excused_trials(campaigns).values())


def entry_status(flags_by_setting: dict[str, list[bool]], excused: int = 0) -> str:
    """Section 5 over an entry's counted repetitions.

    PASS only when every counted repetition in every setting passed; FLAKY when they are
    mixed; FAIL when none passed. Excused trials (``excused``: the entry's restart-only
    trials, left out of ``flags_by_setting``, over both settings and every attempt;
    decision D33) never make an entry FLAKY or FAIL; an entry with more than
    ``MAX_EXCUSED_PER_ENTRY`` of them (D33: "a second excused trial in one entry counts as
    a failure"), or with no counted repetition at all, is ``RESTART_LIMIT``, a failure of
    the entry.
    """
    flags = [f for values in flags_by_setting.values() for f in values]
    if flags and not all(flags):
        return "FLAKY" if any(flags) else "FAIL"
    if excused > MAX_EXCUSED_PER_ENTRY or (not flags and excused):
        return RESTART_LIMIT
    return "PASS" if flags else "FAIL"


def entry_table(
    campaigns: list[dict[str, Any]], excused: dict[str, int] | None = None
) -> dict[str, str]:
    """A1-A3 (decision D33): each entry judged on the counted repetitions of the counting
    attempts, with its excused trials counted over every attempt (a rerun never resets
    them; section 6.1). ``excused`` gives those counts when they are pooled over more than
    these campaigns (A1: both seeds' shuffles); by default they are these campaigns'."""
    flags = outcomes(campaigns, restart_only)
    dropped = excused_trials(every_attempt(campaigns)) if excused is None else excused
    return {
        cell: entry_status(flags.get(cell, {}), dropped.get(cell, 0))
        for cell in sorted(set(flags) | set(dropped))
    }


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


def _judge_entries(
    campaigns: list[dict[str, Any]],
    judged: set[str],
    what: str,
    problems: list[str],
    excused: dict[str, int] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """A1-A3's shared rules (section 5, decisions D30 and D33) over one seed's (A1) or one
    layer's (A2, A3) campaigns: which count, each entry's status on its counted
    repetitions, the judged entries not PASS, and the restart report.

    A restart-only trial is excused: left out of its entry's k of k and listed in the
    restart report. A second excused trial in one entry, over both observation settings
    and every attempt (and, for A1, both seeds' shuffles: ``excused``), fails the entry
    (``RESTART_LIMIT``). An earlier attempt's failed trials count on the judged cells,
    less its excused ones (section 6.1).
    """
    for c in campaigns:
        problems += campaign_problems(c, excused=restart_only, judged=judged)
    status = entry_table(campaigns, excused)
    failing = sorted(cell for cell in judged if status.get(cell) != "PASS")
    if failing:
        problems.append(f"{what} not PASS: {failing}")
    limit = sorted(cell for cell in judged if status.get(cell) == RESTART_LIMIT)
    report = _restart_report(campaigns)
    report["excused_trials"] = _excused_total(every_attempt(campaigns))
    report["entries_over_restart_limit"] = limit
    return status, report


def a1(by_seed: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    """L0-fixed passes 100% of G at 5 repetitions, seeds 43 and 44, both settings, N = 1.

    Each gating entry is judged per seed on its counted repetitions (decision D33); its
    excused trials are counted over both seeds' shuffles, so an entry loses at most one of
    its 20 repetitions in A1 to a restart.
    """
    problems: list[str] = []
    gating = _gating()
    ids = _layer_ids("L0-fixed")
    pooled = excused_trials(every_attempt(c for seed in (43, 44) for c in by_seed.get(seed) or []))
    table, reports = {}, {}
    for seed in (43, 44):
        campaigns = by_seed.get(seed) or []
        if not campaigns:
            problems.append(f"no seed-{seed} campaign")
            continue
        for c in campaigns:
            if c["manifest"]["vm"]["concurrency"] != 1:
                problems.append(f"job {c['job']}: A1 runs at N = 1")
        plan = order.plan(ids, seed, 5, list(SETTINGS), acceptance=True)
        problems += _check_plan(campaigns, expected(plan), f"A1 seed {seed}")
        table[seed], reports[seed] = _judge_entries(
            campaigns, gating, f"seed {seed}: gating entries", problems, pooled
        )
    return _verdict(problems, {"entries": table, "guest_server": reports})


def a2(by_layer: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Each Stage-1 harness passes its gating and declared cells, 5 repetitions, both settings.

    Each in-spec cell is judged on its counted repetitions per layer (decision D33).
    """
    problems: list[str] = []
    cells = _cells()
    table, reports = {}, {}
    for layer in ("H-OSW-fixed", "H-GA"):
        campaigns = by_layer.get(layer) or []
        if not campaigns:
            problems.append(f"no {layer} campaign")
            continue
        plan = order.plan(_layer_ids(layer), 43, 5, list(SETTINGS), acceptance=True)
        problems += _check_plan(campaigns, expected(plan), f"A2 {layer}")
        scored = {c["id"] for c in cells["layers"][layer] if c["status"] in ("gating", "declared")}
        table[layer], reports[layer] = _judge_entries(
            campaigns, scored, f"{layer}: in-spec cells", problems
        )
    return _verdict(problems, {"cells": table, "guest_server": reports})


def a3(by_layer: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """30 stress entries, 60 repetitions (30 per setting), zero failures, on each layer.

    Zero failures among the counted trials; each entry judged on its counted repetitions
    per layer (decision D33).
    """
    problems: list[str] = []
    table, reports = {}, {}
    for layer in ("L0-fixed", "H-OSW-fixed", "H-GA"):
        campaigns = by_layer.get(layer) or []
        if not campaigns:
            problems.append(f"no {layer} campaign")
            continue
        ids = [i for i in _layer_ids(layer) if i in order.STRESS_ENTRIES]
        plan = order.plan(ids, 43, 30, list(SETTINGS), acceptance=True)
        problems += _check_plan(campaigns, expected(plan), f"A3 {layer}")
        table[layer], reports[layer] = _judge_entries(
            campaigns, set(ids), f"{layer}: stress entries", problems
        )
    return _verdict(problems, {"entries": table, "guest_server": reports})


def _restart_report(campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    """Restarts, accessibility calls and every trial a restart hit, over every attempt.

    Section 12: each trial a restart hit, with its job, session (``cycle``), whether the
    restart came during the entry or across the reset observation, its reasons and
    whether it counts (``counted`` is false for an excused, restart-only trial: A1-A4 and
    the ladder leave it out, decisions D30 and D33; A7 judges no trial); and every session
    whose restart count exceeds the restarts attributed to its trials (a restart that hit
    no trial: during the session's start, or between entries when the next pre guard
    already met the new server). ``accessibility_calls`` is over every attempt;
    ``accessibility_calls_counting`` over the counting attempts only (A7's denominator,
    before its cap).
    """
    every = every_attempt(campaigns)
    hit, unattributed = [], []
    for a in every:
        for s in a["sessions"]:
            attributed = 0
            for t in s["trials"]:
                where = [
                    name
                    for name, flag in (
                        ("reset_observation", t.get("reset_restart")),
                        ("entry", RESTART in (t.get("infra") or [])),
                    )
                    if flag
                ]
                if not where:
                    continue
                attributed += len(where)
                hit.append(
                    {
                        "job": a["job"],
                        "cycle": s.get("cycle"),
                        "setting": s["setting"],
                        "seq": t["seq"],
                        "cell": t["cell"],
                        "where": where,
                        "reasons": t.get("reasons"),
                        "counted": not restart_only(t),
                    }
                )
            if (s.get("restarts") or 0) > attributed:
                unattributed.append(
                    {
                        "job": a["job"],
                        "cycle": s.get("cycle"),
                        "setting": s["setting"],
                        "restarts": s.get("restarts"),
                        "attributed": attributed,
                    }
                )
    return {
        "restarts": sum(s.get("restarts") or 0 for a in every for s in a["sessions"]),
        "accessibility_calls": sum(
            s.get("accessibility_calls") or 0 for a in every for s in a["sessions"]
        ),
        "accessibility_calls_counting": sum(
            s.get("accessibility_calls") or 0 for c in campaigns for s in c["sessions"]
        ),
        "trials_hit": hit,
        "sessions_with_unattributed_restarts": unattributed,
        "development_rate": development_rate(),
    }


def a4(campaigns: list[dict[str, Any]], n_star: int) -> dict[str, Any]:
    """The volume plan, zero failures, over the N* VMs; its session slices tile the plan.

    Decision D30: a trial whose only failure is a guest-server restart (``restart_only``:
    during the entry, or across the session's reset observation) is not counted; every
    trial a restart hit is reported with its session and reasons, together with the
    restarts and accessibility calls of every attempt, the sessions whose restarts hit no
    trial and the development rate's single-event uncertainty. Its device actions still
    count toward the class bounds: the action path was judged on that trial and showed no
    difference. A restart outside an observation call (during ``/execute`` or a guard), or
    one slower than ``DesktopEnv``'s retries, leaves another failure in the trial it hits,
    and that trial counts (design decision 40). Unlike A1-A3 and the ladder (decision D33),
    A4 sets no limit on excused trials: A7 bounds the restarts themselves.
    """
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
        problems += campaign_problems(c, excused=restart_only)
        if c["manifest"]["vm"]["concurrency"] != n_star:
            problems.append(f"job {c['job']}: A4 runs at N* = {n_star}")
    ordered = _tiled(campaigns, len(full), "A4", problems)
    problems += _check_plan(ordered, expected(full), "A4")
    trials = [t for c in campaigns for s in c["sessions"] for t in s["trials"]]
    failed = [
        (s["setting"], t["seq"], t["cell"])
        for c in campaigns
        for s in c["sessions"]
        for t in s["trials"]
        if not t["pass"] and not restart_only(t)
    ]
    if failed:
        problems.append(f"A4: {len(failed)} failed trials, first {failed[:5]}")
    return _verdict(
        problems,
        {
            "trials": len(trials),
            "failures": len(failed),
            "restart_only_trials": sum(1 for t in trials if restart_only(t)),
            "guest_server": _restart_report(campaigns),
            "class_actions": plan_data["class_actions"],
            "class_upper_bound_family_95": plan_data["class_upper_bound_family_95"],
            "boot_upper_bound_family_95": plan_data["boot_upper_bound_family_95"],
        },
    )


def _tiled(
    campaigns: list[dict[str, Any]], total: int, what: str, problems: list[str]
) -> list[dict[str, Any]]:
    """The campaigns in session-range order; their ranges must tile ``[0, total)``."""
    ordered = sorted(
        campaigns, key=lambda c: (c["manifest"]["workload"].get("session_range") or [0])[0]
    )
    spans = [c["manifest"]["workload"].get("session_range") or [0, total] for c in ordered]
    if [s[0] for s in spans[1:]] != [s[1] for s in spans[:-1]] or (
        spans and (spans[0][0] != 0 or spans[-1][1] != total)
    ):
        problems.append(f"{what} session ranges {spans} do not tile [0, {total})")
    return ordered


# --- A7: the observation service (decision D30) -------------------------------------------------


def _poisson_cdf(k: int, mean: float) -> float:
    term = total = math.exp(-mean)
    for i in range(1, k + 1):
        term *= mean / i
        total += term
    return total


def poisson_upper(k: int, alpha: float = OBSERVATION_ALPHA) -> float:
    """Exact one-sided upper confidence bound at level 1 - alpha on a Poisson mean.

    The mean m with P(X <= k | m) = alpha (Garwood); k = 0 gives -ln(alpha), 2.996 at 0.05.
    """
    low, high = 0.0, 10.0 * (k + 5)
    for _ in range(200):
        mid = (low + high) / 2
        if _poisson_cdf(k, mid) > alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def poisson_lower(k: int, alpha: float) -> float:
    """Exact one-sided lower bound at level 1 - alpha: P(X >= k | m) = alpha (0 for k = 0)."""
    if k == 0:
        return 0.0
    low, high = 0.0, 10.0 * (k + 5)
    for _ in range(200):
        mid = (low + high) / 2
        if 1.0 - _poisson_cdf(k - 1, mid) < alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def development_rate() -> dict[str, Any]:
    """The development restart rate with its exact two-sided 95% interval (reported only)."""
    k, n = DEVELOPMENT_RESTARTS, DEVELOPMENT_CALLS
    return {
        "restarts": k,
        "accessibility_calls": n,
        "rate": k / n,
        "interval_95": [poisson_lower(k, 0.025) / n, poisson_upper(k, 0.025) / n],
    }


def observation_plan() -> list[dict[str, Any]]:
    """A7's realized order: G, ``OBSERVATION_REPS`` shuffles of seed 43, accessibility only."""
    from harness.q2.vm.manifest import OBSERVATION_REPS

    gating = [c["id"] for c in _cells()["layers"]["L0-fixed"] if c["status"] == "gating"]
    return order.plan(gating, 43, OBSERVATION_REPS, ["screenshot+a11y"], acceptance=True)


def observation_plan_calls() -> int:
    """The accessibility calls A7's plan makes: one per session (the reset observation) and
    one per executed action of each trial (``OBSERVATION_PLAN_CALLS``, section 7)."""
    cells = {c["id"]: c for c in _cells()["layers"]["L0-fixed"]}

    def steps(actions: list[dict[str, Any]]) -> int:
        count = 0
        for action in actions:
            if action["op"] == "terminate":
                break
            count += 1
        return count

    plan = observation_plan()
    return len(plan) + sum(
        steps(cells[cell]["actions"]) for session in plan for _, cell in session["trials"]
    )


def a7(campaigns: list[dict[str, Any]], n_star: int) -> dict[str, Any]:
    """Guest-server restarts per accessibility call: exact 95% upper bound <= 5 x 10^-4.

    The campaign runs L0-fixed over G in the screenshot-plus-accessibility setting
    (``observation_plan``) under attempt 1, at attempt 1's N* (the ``n_star`` argument:
    ``n_star()`` over attempt 1's A1 campaigns and its full ladder; section 11), its
    session slices tiling the plan; a later attempt's N* neither reruns nor re-judges it.
    The restarts k are summed over every attempt of every campaign (section 6.1: an
    attempt that did not count keeps its restarts); the calls n only over the counting
    attempts, so an attempt that was cancelled or did not count adds its restarts and not
    its calls, and stopping a run and rerunning it can never raise A7's chance of passing.
    n is capped at the plan's ``OBSERVATION_PLAN_CALLS`` (decision D33), so no record can
    divide by more calls than the plan makes. Trial verdicts are reported, not judged:
    A1-A4 judge the action path.
    """
    problems: list[str] = []
    full = observation_plan()
    for c in campaigns:
        problems += campaign_problems(c, earlier_failures_count=lambda prev: False)
        if c["manifest"]["vm"]["concurrency"] != n_star:
            problems.append(f"job {c['job']}: A7 runs at N* = {n_star}")
        for attempt in [*c.get("earlier", []), c]:
            if int((attempt["manifest"].get("workload") or {}).get("attempt") or 1) != 1:
                problems.append(f"job {attempt['job']}: A7 runs under attempt 1 only")
    ordered = _tiled(campaigns, len(full), "A7", problems)
    problems += _check_plan(ordered, expected(full), "A7")
    report = _restart_report(campaigns)
    restarts = report["restarts"]
    calls = min(report["accessibility_calls_counting"], OBSERVATION_PLAN_CALLS)
    upper = poisson_upper(restarts) / calls if calls else None
    counting = [s for c in campaigns for s in c["sessions"]]
    # Reported, not judged: two development faults cannot show whether restarts cluster at
    # a session's start, which a per-call bound would hide (section 9). Same rule: the
    # restarts of every attempt over the sessions of the counting attempts.
    every = [s for a in every_attempt(campaigns) for s in a["sessions"]]
    per_session = {
        "sessions": len(counting),
        "sessions_with_restart": sum(1 for s in every if s.get("restarts")),
        "rate": restarts / len(counting) if counting else None,
        "upper_95": poisson_upper(restarts) / len(counting) if counting else None,
    }
    if upper is None or upper > OBSERVATION_BOUND:
        problems.append(
            f"A7: {restarts} restarts in {calls} accessibility calls, upper 95% bound "
            f"{upper} > {OBSERVATION_BOUND}"
        )
    return _verdict(
        problems,
        {
            "restarts": restarts,
            "accessibility_calls": calls,
            "accessibility_calls_counting": report["accessibility_calls_counting"],
            "accessibility_calls_every_attempt": report["accessibility_calls"],
            "plan_calls": OBSERVATION_PLAN_CALLS,
            "rate": restarts / calls if calls else None,
            "upper_95": upper,
            "bound": OBSERVATION_BOUND,
            "per_session": per_session,
            "failed_trials": sum(len(failed_trials(c)) for c in campaigns),
            "guest_server": report,
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
    """The detection controls fail their known-defect cells in 5 of 5 repetitions.

    An earlier attempt (section 6.1) is judged by C1's own rule: its failures are what C1
    requires (a known-defect cell fails by design, and C1 judges no other cell), so they
    never count against it, while a known-defect cell that passed in any trial of any
    attempt does.
    """
    problems: list[str] = []
    table = {}
    for layer, must_fail in C1_MUST_FAIL.items():
        campaigns = by_layer.get(layer) or []
        if not campaigns:
            problems.append(f"no {layer} campaign")
            continue
        for c in campaigns:
            problems += campaign_problems(c, earlier_failures_count=lambda prev: False)
            for previous in c.get("earlier") or []:
                passed = sorted(
                    {
                        t["cell"]
                        for s in previous["sessions"]
                        for t in s["trials"]
                        if t["pass"] and t["cell"] in must_fail
                    }
                )
                if passed:
                    problems.append(
                        f"job {c['job']}: earlier attempt {previous['job']} passed "
                        f"known-defect cells {passed}"
                    )
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
    reported next to it as ``strict_entries``. An earlier attempt's trials are read the
    same way (section 6.1): a failure counts against C2 only on a cell outside the
    predicted set, where every repetition must pass; the predicted cells are judged on
    the counting attempt.
    """
    import yaml

    problems: list[str] = []
    predicted = set(yaml.safe_load(PREDICTION.read_text(encoding="utf-8"))["predicted_fail"])
    cells = {c["id"]: c for c in _cells()["layers"]["L0-fixed"]}

    def read_as_pass(trial: dict[str, Any]) -> bool:
        return c2_trial_pass(trial, cells.get(trial["cell"]) or {})

    for c in campaigns:
        problems += campaign_problems(c, excused=read_as_pass, judged=set(cells) - predicted)
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

    Earlier attempts (section 6.1) are read by C3's own rule. A mutant's failures are its
    kills, never failures against C3: its kills and its equivalence are read from the
    counting attempt, and each earlier attempt is reported with its failed cells and
    whether its signature matched the reference's on the cells it ran. The reference's
    failures are what keep a cell from killing: a cell the reference failed, or failed
    with an infrastructure failure, in any of its attempts cannot kill.
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
            # An earlier reference attempt's failures act through reference_results.
            problems += campaign_problems(c, earlier_failures_count=lambda prev: False)
    for layer, campaigns in references.items():
        plan = order.plan(_layer_ids(layer), 42, 1, ["screenshot"])
        problems += _check_plan(campaigns, expected(plan), f"C3 reference {layer}")
    # Over every attempt: a cell the reference did not pass cleanly in one cannot kill.
    reference_results = {layer: _cell_results(every_attempt(c)) for layer, c in references.items()}
    reference_signatures = {layer: _signature(c) for layer, c in references.items()}
    table = {}
    for operator, layer in kit.scored_pairs(operators):
        key = f"{operator} {layer}"
        campaigns = mutants.get((operator, layer)) or []
        if not campaigns:
            problems.append(f"{operator} on {layer}: no run")
            continue
        for c in campaigns:
            # A mutant's failures are kills: an earlier attempt's are reported below.
            problems += campaign_problems(c, earlier_failures_count=lambda prev: False)
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
        signature = reference_signatures.get(layer) or {}
        entry = {
            "killers": killers,
            "predicted_killers": predicted_cells.get((operator, layer), []),
            "infra_cells": infra_cells,
            "reference_not_clean": reference_not_clean,
            # Reported, not judged (section 6.1).
            "earlier_attempts": [
                {
                    "job": previous["job"],
                    "failed_cells": sorted({cell for _, _, cell in failed_trials(previous)}),
                    "signature_matches_reference": all(
                        signature.get(cell) == values
                        for cell, values in _signature([previous]).items()
                    ),
                }
                for c in campaigns
                for previous in c.get("earlier") or []
            ],
        }
        if killers:
            entry["outcome"] = "killed"
        elif references.get(layer) and _signature(campaigns) == signature:
            entry["outcome"] = "equivalent"
        else:
            entry["outcome"] = "survived"
            problems.append(f"{operator} on {layer} survived and is not equivalent")
        table[key] = entry
    return _verdict(problems, {"mutants": table})


def c4(a1_campaigns: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """In every A1 trial of an entry with an R-dev reference, the projection matches.

    Every attempt's trials count (section 6.1): C4 reads the tap's stream, which A1 does
    not judge for an entry the probe observes, so an earlier attempt's mismatch there
    would otherwise disappear with a rerun.
    """
    problems: list[str] = []
    checked = 0
    for c in every_attempt(a1_campaigns):
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
    """Section 9: a foreign Slurm job started, or foreign jobs held more than 8 CPUs.

    These are the only two reasons that abort a rung. With no host snapshot there is no
    abort to read (empty); ``snapshot_problems`` reports the missing snapshots instead.
    """
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
        return []
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


def snapshot_problems(campaign: dict[str, Any]) -> list[str]:
    """The sessions whose host snapshots (before and after) are missing (section 9).

    The driver writes them into each session's record file after the VM's teardown, so a
    job killed while its first sessions ran, or a run directory copied without its record
    files, has none for those sessions. Such a rung attempt cannot show that no abort
    occurred: it does not qualify and may be rerun once, like a campaign that did not
    count. It is not an abort: its failed and excused trials count (section 6.1).
    """
    sessions = campaign["sessions"]
    missing = [s.get("cycle") for s in sessions if not all(s.get("snapshots") or [None])]
    if not sessions:
        return [f"job {campaign['job']}: no session, so no host snapshots"]
    if missing:
        return [
            f"job {campaign['job']}: host snapshots missing for {len(missing)} of "
            f"{len(sessions)} sessions, first {missing[:5]}"
        ]
    return []


def rung(campaigns: list[dict[str, Any]], step_p95_n1: float) -> dict[str, Any]:
    """Whether one ladder rung qualifies (section 9), with its measurements.

    Decision D33: "every gating trial passes" reads over the rung's counted gating trials
    (a restart-only trial is excused and listed in the restart report), and a rung with
    more than ``MAX_EXCUSED_PER_RUNG`` excused trials, gating or not, over its attempts
    (an aborted attempt aside, section 9) does not qualify. Excused trials' steps stay in
    the step p95, and the foreign-load abort is unchanged. Only ``foreign_abort``'s two
    reasons abort a rung: an attempt missing host snapshots (``snapshot_problems``) does
    not qualify and may be rerun, but its failed and excused trials count.
    """
    from harness.q2.vm.manifest import ladder_reps

    problems: list[str] = []
    n = campaigns[0]["manifest"]["vm"]["concurrency"]
    gating = _gating()

    def rerun_allowed(previous: dict[str, Any]) -> bool:
        # Section 9: an aborted rung, one without its host snapshots, or one that did not
        # count is rerun once.
        return bool(
            counting_problems(previous) or foreign_abort(previous) or snapshot_problems(previous)
        )

    def not_aborted(previous: dict[str, Any]) -> bool:
        # Section 9: an aborted attempt's trials are reported and never counted; missing
        # snapshots are not an abort.
        return not foreign_abort(previous)

    earlier = []
    for c in campaigns:
        problems += campaign_problems(
            c, rerun_allowed, not_aborted, excused=restart_only, judged=gating
        )
        problems += snapshot_problems(c)
        if c["manifest"]["vm"]["concurrency"] != n:
            problems.append("a rung's campaigns run at one concurrency")
        for previous in c.get("earlier") or []:
            earlier.append(
                {
                    "job": previous["job"],
                    "abort_reasons": foreign_abort(previous),
                    "snapshot_problems": snapshot_problems(previous),
                    "failed_trials": len(failed_trials(previous)),
                    "excused_trials": _excused_total([previous]),
                }
            )
    aborts = sorted({r for c in campaigns for r in foreign_abort(c)})
    plan = order.plan(_layer_ids("L0-fixed"), 43, ladder_reps(n), list(SETTINGS), acceptance=True)
    problems += _check_plan(campaigns, expected(plan), f"rung N={n}")
    boots = [s["boot_s"] for c in campaigns for s in c["sessions"] if s["boot_s"] is not None]
    # Every trial's steps, excused ones included (decision D33).
    steps = [x for c in campaigns for s in c["sessions"] for t in s["trials"] for x in t["steps_s"]]
    boot_p95, step_p95 = quantile(boots, 0.95), quantile(steps, 0.95)
    if len(boots) < MIN_RUNG_BOOTS:
        problems.append(f"{len(boots)} cold boots measured (at least {MIN_RUNG_BOOTS})")
    if boot_p95 is None or boot_p95 > BOOT_P95_MAX_S:
        problems.append(f"boot p95 {boot_p95} s > {BOOT_P95_MAX_S} s")
    if step_p95 is None or step_p95 > STEP_P95_FACTOR * step_p95_n1:
        problems.append(f"step p95 {step_p95} s > {STEP_P95_FACTOR} x {step_p95_n1} s")
    status = {cell: entry_status(v) for cell, v in outcomes(campaigns, restart_only).items()}
    failing = sorted(cell for cell in gating if status.get(cell) != "PASS")
    if failing:
        problems.append(f"gating entries not PASS: {failing}")
    counted_earlier = [p for c in campaigns for p in c.get("earlier") or [] if not_aborted(p)]
    excused = _excused_total([*counted_earlier, *campaigns])
    if excused > MAX_EXCUSED_PER_RUNG:
        problems.append(f"{excused} excused trials (at most {MAX_EXCUSED_PER_RUNG})")
    return {
        "n": n,
        "aborted": bool(aborts),
        "abort_reasons": aborts,
        "qualifies": not problems and not aborts,
        "problems": problems,
        "boots": len(boots),
        "boot_p95_s": boot_p95,
        "step_p95_s": step_p95,
        "excused_trials": excused,
        "guest_server": _restart_report(campaigns),
        "earlier_attempts": earlier,
    }


def n_star(a1_campaigns: list[dict[str, Any]], rungs: dict[int, list[dict[str, Any]]]) -> dict:
    """N*: the largest rung that qualifies; 1 when none does (A1 gates N = 1 itself).

    A1's step p95 pools every trial's steps, excused ones included (decision D33).
    """
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
