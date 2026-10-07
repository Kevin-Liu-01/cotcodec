"""VM time of the q2-action-path-v1 campaigns, from measured development trial times.

Preregistration section 9 ("Cost") sizes every scored campaign in VM-hours: the time
one desktop VM is occupied, summed over VMs (wall-clock time at concurrency N is about
VM-hours / N when the per-trial time does not grow with N, which the ladder measures).

Model, per campaign: the sum over its trials of the measured mean time of that trial's
(layer, observation setting, cell), plus, per session, the measured mean session overhead
(cold boot to settled screen, probe and tap start, final guard, container removal), plus,
per Slurm job, the measured job overhead (preflight and the qcow2 digest before and after).
Trial time is the runner's ``timing_s.total`` (pre guard, every ``DesktopEnv.step`` with
its observation, post guard), so it includes the accessibility tree in the
``screenshot+a11y`` setting.

Two stages:

* ``extract`` (on the host, standard library only) reads development run directories
  (``manifest.json``, ``receipt.json``, ``cycles/cycle-NN.json``, ``cycles/record-NN.json``)
  and writes the measured times with each receipt's SHA-256; a boot-reset validation run
  supplies the cycle time of A5;
* ``plan`` turns those times into VM-hours per campaign using the frozen session rules
  (``order.plan``, ``volume.sessions``) and writes ``vm_hours.json``. A cell with no
  measurement in a layer takes the value the table names (``FALLBACK``), and the output
  lists every such substitution.

Usage::

    python3 -m harness.q2.action_path.vm_hours extract RUN_DIR... > trial-times.json
    python3 -m harness.q2.action_path.vm_hours plan trial-times.json > vm_hours.json
"""

from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import statistics
import sys
from pathlib import Path
from typing import Any

from harness.q2.action_path import order

ROOT = Path(__file__).resolve().parents[3]
CELLS = ROOT / "harness/q2/action_path/suite_cells.json"
VOLUME_PLAN = ROOT / "harness/q2/action_path/volume_plan.json"
OPERATORS = ROOT / "harness/q2/action_path/mutation_operators.yaml"
SETTINGS = order.SETTINGS
LADDER_RUNGS = (8, 16, 24, 32, 40)
# Layers never run in development (they are scored once, on frozen code) take the times
# of the layer that executes the same cells through the same executor.
FALLBACK = {"L0-raw": "L0-fixed", "H-OSW-up": "H-OSW-fixed", "H-GA-buggy": "H-GA"}
SCHEMA = "cotcodec-q2-vm-hours-v1"


# --- extraction (host side) ------------------------------------------------------------------


def _sha256(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _load(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def extract(run_dirs: list[str]) -> dict[str, Any]:
    """Measured trial, session and job times of development runs (see the module doc)."""
    trials: dict[str, dict[str, dict[str, list[float]]]] = {}
    canary: dict[str, list[float]] = {}
    sessions: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        receipt_path = os.path.join(run_dir, "receipt.json")
        receipt = _load(receipt_path)
        manifest = _load(os.path.join(run_dir, "manifest.json"))
        kind = manifest["workload"]["kind"]
        cycle_full = 0.0
        layer = None
        for path in sorted(glob.glob(os.path.join(run_dir, "cycles", "cycle-[0-9][0-9].json"))):
            cycle = _load(path)
            record_path = path.replace("cycle-", "record-")
            record = _load(record_path)
            full = record["host_after"]["t"] - record["host_before"]["t"]
            cycle_full += full
            layer = cycle.get("layer")
            setting = cycle.get("setting")
            trial_sum = 0.0
            for trial in cycle.get("trials") or []:
                timing = trial.get("timing_s")
                # Suite trials record a breakdown; canary trials record one number.
                total = timing.get("total") if isinstance(timing, dict) else timing
                if total is None:
                    continue
                trial_sum += total
                if kind == "canary-development":
                    canary.setdefault(trial["cell"], []).append(total)
                else:
                    by_cell = trials.setdefault(layer, {}).setdefault(setting, {})
                    by_cell.setdefault(trial["cell"], []).append(total)
            sessions.append(
                {
                    "job": receipt["job_id"],
                    "cycle": cycle["cycle"],
                    "kind": kind,
                    "setting": setting,
                    "trials": len(cycle.get("trials") or []),
                    "full_s": round(full, 3),
                    "overhead_s": round(full - trial_sum, 3),
                    "boot_s": (cycle.get("boot") or {}).get("t_screenshot_200"),
                    "settled_s": (cycle.get("settle") or {}).get("t_settled"),
                }
            )
        jobs.append(
            {
                "job": receipt["job_id"],
                "campaign_id": receipt["campaign_id"],
                "kind": kind,
                "git_sha": receipt["git_sha"],
                "receipt_sha256": _sha256(receipt_path),
                "layer": layer,
                "wall_s": round(receipt["finished_at"] - receipt["started_at"], 3),
                "overhead_s": round(receipt["finished_at"] - receipt["started_at"] - cycle_full, 3),
            }
        )
    return {
        "schema": "cotcodec-q2-trial-times-v1",
        "jobs": jobs,
        "sessions": sessions,
        "trials": {
            layer: {
                setting: {cell: [round(t, 4) for t in vals] for cell, vals in sorted(by.items())}
                for setting, by in sorted(per.items())
            }
            for layer, per in sorted(trials.items())
        },
        "canary": {cell: [round(t, 4) for t in values] for cell, values in sorted(canary.items())},
    }


# --- planning ----------------------------------------------------------------------------------


def _mean(values: list[float]) -> float:
    return statistics.fmean(values)


class Times:
    """Mean trial time per (layer, setting, cell), with recorded fallbacks."""

    def __init__(self, measured: dict[str, Any]):
        self.trials = measured["trials"]
        self.canary = measured["canary"]
        suite = [s for s in measured["sessions"] if s["kind"] == "suite-development"]
        self.session_overhead_s = _mean([s["overhead_s"] for s in suite])
        self.job_overhead_s = _mean([j["overhead_s"] for j in measured["jobs"]])
        self.boot_s = sorted(s["boot_s"] for s in suite if s["boot_s"] is not None)
        resets = [s for s in measured["sessions"] if s["kind"] == "boot-reset-validation"]
        self.boot_reset_cycle_s = _mean([s["full_s"] for s in resets])
        self.substitutions: dict[str, int] = {}

    def trial(self, layer: str, setting: str, cell: str) -> float:
        source = FALLBACK.get(layer, layer)
        values = (self.trials.get(source) or {}).get(setting, {}).get(cell)
        if source != layer:
            self.substitutions[f"{layer} <- {source}"] = (
                self.substitutions.get(f"{layer} <- {source}", 0) + 1
            )
        if values is None and source != "L0-fixed":
            values = (self.trials.get("L0-fixed") or {}).get(setting, {}).get(cell)
            if values is not None:
                key = f"{layer}:{cell} <- L0-fixed"
                self.substitutions[key] = self.substitutions.get(key, 0) + 1
        if values is None:
            raise KeyError(f"no measured time for {layer} {setting} {cell}")
        return _mean(values)


def _seconds(times: Times, layer: str, sessions: list[dict[str, Any]], jobs: int) -> dict:
    trial_s = sum(
        times.trial(layer, session["setting"], cell)
        for session in sessions
        for _, cell in session["trials"]
    )
    count = sum(len(session["trials"]) for session in sessions)
    vm_s = trial_s + len(sessions) * times.session_overhead_s + jobs * times.job_overhead_s
    return {
        "trials": count,
        "sessions": len(sessions),
        "jobs": jobs,
        "trial_s": round(trial_s, 1),
        "vm_hours": round(vm_s / 3600.0, 3),
    }


def _layer_ids(cells: dict[str, Any], layer: str) -> list[str]:
    return [c["id"] for c in cells["layers"][layer]]


def plan(measured: dict[str, Any]) -> dict[str, Any]:
    """VM-hours per scored campaign (preregistration sections 7-9)."""
    from harness.q2.action_path import volume

    cells = json.loads(CELLS.read_text(encoding="utf-8"))
    volume_plan = json.loads(VOLUME_PLAN.read_text(encoding="utf-8"))
    times = Times(measured)
    both = list(SETTINGS)
    out: dict[str, Any] = {}

    def run(name: str, layer: str, ids: list[str], seed: int, reps: int, settings: list[str]):
        sessions = order.plan(ids, seed, reps, settings, acceptance=seed != 42)
        out[name] = _seconds(times, layer, sessions, jobs=1)

    for seed in (43, 44):
        run(f"A1 seed {seed}", "L0-fixed", _layer_ids(cells, "L0-fixed"), seed, 5, both)
    for layer in ("H-OSW-fixed", "H-GA"):
        run(f"A2 {layer}", layer, _layer_ids(cells, layer), 43, 5, both)
    for layer in ("L0-fixed", "H-OSW-fixed", "H-GA"):
        ids = [i for i in _layer_ids(cells, layer) if i in order.STRESS_ENTRIES]
        run(f"A3 {layer}", layer, ids, 43, 30, both)
    realized = volume.sessions(volume_plan, 43)
    a4 = [
        {"setting": setting, "trials": list(enumerate(chunk))}
        for setting in SETTINGS
        for chunk in realized[setting]
    ]
    out["A4"] = _seconds(times, "L0-fixed", a4, jobs=1)
    from harness.q2.vm.manifest import OBSERVATION_REPS

    # A7 (decision D30): G in the screenshot-plus-accessibility setting, seed-43 shuffles.
    gating = [c["id"] for c in cells["layers"]["L0-fixed"] if c["status"] == "gating"]
    run("A7", "L0-fixed", gating, 43, OBSERVATION_REPS, ["screenshot+a11y"])
    for rung in LADDER_RUNGS:
        from harness.q2.vm.manifest import ladder_reps

        run(f"ladder N={rung}", "L0-fixed", _layer_ids(cells, "L0-fixed"), 43,
            ladder_reps(rung), both)  # fmt: skip
    from harness.q2.vm.manifest import CANARY_APPS

    # The driver's order: the apps as A6's manifest lists them, then each app's entries.
    apps = cells["canary"]["apps"]
    pairs = [f"{app}:{entry}" for app in CANARY_APPS for entry in apps[app]["entries"]]
    canary_sessions = order.plan(pairs, 43, 5, ["screenshot"], acceptance=True)
    canary_s = sum(_mean(times.canary[cell]) for s in canary_sessions for _, cell in s["trials"])
    canary_vm = canary_s + len(canary_sessions) * times.session_overhead_s + times.job_overhead_s
    out["A6"] = {
        "trials": sum(len(s["trials"]) for s in canary_sessions),
        "sessions": len(canary_sessions),
        "jobs": 1,
        "trial_s": round(canary_s, 1),
        "vm_hours": round(canary_vm / 3600.0, 3),
    }
    # A5: a boot-reset campaign with 20 reset checks (21 cold boots) at the frozen SHA.
    a5_s = 21 * times.boot_reset_cycle_s + times.job_overhead_s
    out["A5"] = {"trials": 0, "sessions": 21, "jobs": 1, "trial_s": 0.0,
                 "vm_hours": round(a5_s / 3600.0, 3)}  # fmt: skip
    for layer in ("H-OSW-up", "H-GA-buggy"):
        run(f"C1 {layer}", layer, _layer_ids(cells, layer), 42, 5, ["screenshot"])
    run("C2 L0-raw", "L0-raw", _layer_ids(cells, "L0-fixed"), 42, 5, ["screenshot"])
    c3 = _c3(times, cells)
    out.update(c3)
    total = sum(v["vm_hours"] for v in out.values())
    a4_hours = out["A4"]["vm_hours"]
    a7_hours = out["A7"]["vm_hours"]
    return {
        "schema": SCHEMA,
        "measured_from": [
            {k: j[k] for k in ("job", "campaign_id", "git_sha", "receipt_sha256")}
            for j in measured["jobs"]
        ],
        "model": {
            "session_overhead_s": round(times.session_overhead_s, 3),
            "job_overhead_s": round(times.job_overhead_s, 3),
            "boot_reset_cycle_s": round(times.boot_reset_cycle_s, 3),
            "boot_s_p50": _quantile(times.boot_s, 0.5),
            "boot_s_p95": _quantile(times.boot_s, 0.95),
            "substitutions": dict(sorted(times.substitutions.items())),
        },
        "campaigns": out,
        "total_vm_hours": round(total, 2),
        "a4_wall_hours_at_concurrency": [[n, round(a4_hours / n, 2)] for n in (1, *LADDER_RUNGS)],
        "a7_wall_hours_at_concurrency": [[n, round(a7_hours / n, 2)] for n in (1, *LADDER_RUNGS)],
    }


def _c3(times: Times, cells: dict[str, Any]) -> dict[str, Any]:
    """C3: one full-layer pass per scored mutant, plus one unmutated reference per layer."""
    import yaml

    operators = yaml.safe_load(OPERATORS.read_text(encoding="utf-8"))
    from harness.q2.action_path import mutants

    counts: dict[str, int] = {}
    for _, layer in mutants.scored_pairs(operators):
        counts[layer] = counts.get(layer, 0) + 1
    out = {}
    for layer, count in sorted(counts.items()):
        sessions = order.plan(_layer_ids(cells, layer), 42, 1, ["screenshot"])
        one = _seconds(times, layer, sessions, jobs=1)
        runs = count + 1
        out[f"C3 {layer}"] = {
            "trials": one["trials"] * runs,
            "sessions": one["sessions"] * runs,
            "jobs": runs,
            "trial_s": round(one["trial_s"] * runs, 1),
            "vm_hours": round(one["vm_hours"] * runs, 3),
        }
    return out


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    rank = max(1, math.ceil(q * len(values)))
    return values[rank - 1]


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "extract":
        json.dump(extract(argv[1:]), sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 2 and argv[0] == "plan":
        measured = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        json.dump(plan(measured), sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    sys.stderr.write(__doc__ or "")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
