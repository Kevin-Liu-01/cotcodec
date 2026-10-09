#!/usr/bin/env python3
"""Acceptance verdicts of q2-action-path-v2 at N = 1 (A1 with C4, A2, A3, A5, A6).

Runs on the host from the read-only export of the frozen commit: it imports that export's
``harness.q2.action_path.acceptance`` (frozen in the inputs addendum and pinned again in the
executor addendum) and calls ``acceptance.a1`` (and ``acceptance.c4`` over A1's
campaigns), ``a2``, ``a3``, ``a5`` or ``a6`` on the campaigns ``acceptance.load`` reads from
the run directories. Nothing in a verdict is computed here; this script only groups the run
directories by campaign (attempts in the order they ran) and writes, as JSON, the verdict,
the section-12 report of key events read without their state
(``acceptance.state_not_observed_report``, which every verdict carries under
``state_not_observed``; written again on its own) and a per-campaign summary (end state,
counting problems, per-cell pass counts per setting, every failed trial with its reasons,
retries, boots, steps, restarts).

    python3 -B analyze_acceptance.py EXPORT RUNS OUT_DIR CRITERION ATTEMPTS.json [MORE.json...]

CRITERION is A1, A2, A3, A5 or A6. ATTEMPTS.json maps each campaign id to its job ids in
attempt order (first, then a rerun under section 6.1). For A5, ATTEMPTS.json holds the
boot-reset campaign and MORE.json files hold the acceptance campaigns whose receipts A5
reads; A5 is judged against the export commit every scored campaign runs from (``SHA``).
For A1 the script also writes C4 (``acceptance.c4`` over A1's campaigns) and A1's N = 1
reference for the ladder (the step p95 over every A1 step, both shuffles and settings
pooled, excused trials included, as ``acceptance.n_star`` computes it; and boot p50/p95).
The validity-control script (``analyze_controls.py``) is the model.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
from typing import Any

# The commit every scored campaign of q2-action-path-v2 runs from (the export that records
# ledger row 15); A5's boot-reset campaign must run at it (acceptance.a5).
SHA = "bf99a645c3782b2c59a75b6f463461b2515d0d97"


def sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def criterion_of(manifest: dict[str, Any]) -> str | None:
    workload = manifest.get("workload") or {}
    if workload.get("kind") == "canary-acceptance":
        return "A6"
    if workload.get("kind") == "boot-reset-validation":
        return "A5"
    return workload.get("criterion")


def main() -> int:
    export, runs, out_dir, criterion, attempts_path, *more = sys.argv[1:]
    sys.path.insert(0, export)
    from harness.q2.action_path import acceptance as acc

    def read_attempts(path: str) -> dict[str, list[str]]:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def load(jobs: list[str]) -> dict[str, Any]:
        earlier = [acc.load(os.path.join(runs, job)) for job in jobs[:-1]]
        return acc.load(os.path.join(runs, jobs[-1]), earlier=earlier)

    def load_all(attempts: dict[str, list[str]], want: set[str]) -> dict[str, dict[str, Any]]:
        out = {}
        for campaign_id, jobs in attempts.items():
            c = load(jobs)
            if criterion_of(c["manifest"]) not in want:
                continue
            if c["manifest"].get("campaign_id") != campaign_id:
                ran = c["manifest"].get("campaign_id")
                raise SystemExit(f"{campaign_id}: job {jobs[-1]} ran {ran}")
            for previous in c["earlier"]:
                if previous["manifest"].get("campaign_id") != campaign_id:
                    other = previous["job"]
                    raise SystemExit(f"{campaign_id}: earlier job {other} is another campaign")
            out[campaign_id] = c
        return out

    attempts = read_attempts(attempts_path)
    campaigns = load_all(attempts, {criterion})
    if not campaigns:
        raise SystemExit(f"no {criterion} campaign in {attempts_path}")
    jobs_of = dict(attempts)
    extra: dict[str, Any] = {}

    if criterion == "A1":
        by_seed: dict[int, list[dict[str, Any]]] = {}
        for c in campaigns.values():
            by_seed.setdefault(c["manifest"]["randomness"]["seeds"][0], []).append(c)
        verdict = acc.a1(by_seed)
        a1_campaigns = [c for seed in (43, 44) for c in by_seed.get(seed) or []]
        extra["c4"] = acc.c4(a1_campaigns)
        steps = [x for c in a1_campaigns for s in c["sessions"] for t in s["trials"]
                 for x in t["steps_s"]]  # fmt: skip
        boots = [s["boot_s"] for c in a1_campaigns for s in c["sessions"]
                 if s["boot_s"] is not None]  # fmt: skip
        extra["a1-n1-reference"] = {
            "what": "A1's N = 1 reference for the ladder (section 9): every A1 step, both "
            "shuffles and both settings pooled, excused trials included (acceptance.n_star)",
            "steps": len(steps),
            "step_p50_s": acc.quantile(steps, 0.5),
            "step_p95_s": acc.quantile(steps, 0.95),
            "boots": len(boots),
            "boot_p50_s": acc.quantile(boots, 0.5),
            "boot_p95_s": acc.quantile(boots, 0.95),
        }
    elif criterion in ("A2", "A3"):
        by_layer: dict[str, list[dict[str, Any]]] = {}
        for c in campaigns.values():
            by_layer.setdefault(c["manifest"]["workload"]["layer"], []).append(c)
        verdict = acc.a2(by_layer) if criterion == "A2" else acc.a3(by_layer)
    elif criterion == "A6":
        verdict = acc.a6(list(campaigns.values()))
    elif criterion == "A5":
        if len(campaigns) != 1:
            raise SystemExit(f"A5 has one boot-reset campaign, not {len(campaigns)}")
        acceptance: dict[str, dict[str, Any]] = {}
        for path in more:
            found = read_attempts(path)
            jobs_of.update(found)
            acceptance.update(load_all(found, {"A1", "A2", "A3", "A4", "A6", "A7", "ladder"}))
        (boot_reset,) = campaigns.values()
        verdict = acc.a5(boot_reset, list(acceptance.values()), SHA)
        verdict["acceptance_campaigns_read"] = sorted(acceptance)
        campaigns = {**campaigns, **acceptance}
    else:
        raise SystemExit(f"unknown criterion {criterion}")

    def per_cell(c: dict[str, Any]) -> dict[str, dict[str, str]]:
        counts: dict[str, dict[str, list[int]]] = {}
        for s in c["sessions"]:
            for t in s["trials"]:
                row = counts.setdefault(t["cell"], {}).setdefault(s["setting"], [0, 0])
                row[0] += 1 if t["pass"] else 0
                row[1] += 1
        return {
            cell: {setting: f"{k}/{n}" for setting, (k, n) in sorted(v.items())}
            for cell, v in sorted(counts.items())
        }

    def summary(campaign_id: str, c: dict[str, Any]) -> dict[str, Any]:
        receipt = c["receipt"]
        trials = [(s, t) for s in c["sessions"] for t in s["trials"]]
        steps = [x for _, t in trials for x in t["steps_s"]]
        boots = [s.get("boot_s") for s in c["sessions"] if s.get("boot_s") is not None]
        infra = collections.Counter(k for _, t in trials for k in t["infra"])
        retried = collections.Counter(k for _, t in trials for k in t["retried"])
        c4 = collections.Counter(str(t["c4"]) for _, t in trials if t["c4"] is not None)
        w = c["manifest"].get("workload") or {}
        out = {
            "campaign_id": campaign_id,
            "criterion": criterion_of(c["manifest"]),
            "kind": w.get("kind"),
            "layer": w.get("layer"),
            "seed": (c["manifest"].get("randomness") or {}).get("seeds"),
            "settings": w.get("settings"),
            "attempt": w.get("attempt"),
            "concurrency": (c["manifest"].get("vm") or {}).get("concurrency"),
            "jobs": jobs_of.get(campaign_id),
            "job": c["job"],
            "earlier_attempts": [e["job"] for e in c["earlier"]],
            "git_sha": c["manifest"].get("git_sha"),
            "tree_sha256": (c["manifest"].get("source") or {}).get("tree_sha256"),
            "slurm": c["slurm"],
            "batch": c["batch"],
            "counting_problems": acc.counting_problems(c),
            "infra_gates_pass": (receipt.get("summary") or {}).get("infra_gates_pass"),
            "qcow2_unchanged": receipt.get("qcow2_unchanged"),
            "labelled_containers_left": receipt.get("labelled_containers_left"),
            "leaked_volumes": (receipt.get("summary") or {}).get("leaked_volumes"),
            "no_gpu_all": (receipt.get("summary") or {}).get("no_gpu_all"),
            "unreadable": c["unreadable"],
            "receipt_sha256": sha256(os.path.join(c["run_dir"], "receipt.json")),
            "manifest_json_sha256": sha256(os.path.join(c["run_dir"], "manifest.json")),
            "started_at": receipt.get("started_at"),
            "finished_at": receipt.get("finished_at"),
            "sessions": len(c["sessions"]),
            "trials": len(trials),
            "trials_pass": sum(1 for _, t in trials if t["pass"]),
            "per_cell_pass": per_cell(c),
            "failed_trials": [
                {
                    "cycle": s.get("cycle"),
                    "setting": s["setting"],
                    "seq": t["seq"],
                    "cell": t["cell"],
                    "infra": t["infra"],
                    "reasons": t["reasons"],
                    "restart_only": acc.restart_only(t),
                }
                for s, t in trials
                if not t["pass"]
            ],
            "infra_types": dict(infra),
            "observation_retries": dict(retried),
            "reset_observations": [s.get("reset_observation") for s in c["sessions"]],
            "session_errors": [s.get("error") for s in c["sessions"] if s.get("error")],
            "c4_flags": dict(c4),
            "boot_s": {
                "n": len(boots),
                "p50": acc.quantile(boots, 0.5),
                "p95": acc.quantile(boots, 0.95),
                "max": max(boots) if boots else None,
            },
            "step_s": {
                "n": len(steps),
                "p50": acc.quantile(steps, 0.5),
                "p95": acc.quantile(steps, 0.95),
            },
            "restarts": sum(s.get("restarts") or 0 for s in c["sessions"]),
            "accessibility_calls": sum(s.get("accessibility_calls") or 0 for s in c["sessions"]),
        }
        if w.get("kind") == "boot-reset-validation":
            out["receipt_summary"] = receipt.get("summary")
        return out

    os.makedirs(out_dir, exist_ok=True)
    tag = criterion.lower()

    def write(name: str, value: Any) -> None:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")

    write(f"{tag}-verdict.json", verdict)
    if "state_not_observed" in verdict:
        write(f"{tag}-section12-state-not-observed.json", verdict["state_not_observed"])
    write(f"{tag}-campaigns.json", [summary(k, c) for k, c in sorted(campaigns.items())])
    if "c4" in extra:
        write("c4-verdict.json", extra["c4"])
        write("c4-section12-state-not-observed.json", extra["c4"]["state_not_observed"])
    if "a1-n1-reference" in extra:
        write("a1-n1-reference.json", extra["a1-n1-reference"])
    report = verdict.get("state_not_observed") or {}
    print(json.dumps({"criterion": criterion, "pass": verdict["pass"],
                      "problems": verdict["problems"], "campaigns": len(campaigns),
                      "c4_pass": (extra.get("c4") or {}).get("pass"),
                      "section12_trials": report.get("trials"),
                      "read_without_state": len(report.get("read_without_state") or []),
                      "no_processed_press_before":
                          len(report.get("no_processed_press_before") or [])}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
