#!/usr/bin/env python3
"""Validity-control verdicts of q2-action-path-v1 (C1, C2, C3) with the frozen analysis.

Runs on the host from the read-only export of the frozen commit: it imports that export's
``harness.q2.action_path.acceptance`` (frozen in the inputs addendum and pinned again in the
executor addendum) and calls ``acceptance.c1``, ``acceptance.c2`` or ``acceptance.c3`` on
the campaigns ``acceptance.load`` reads from the run directories. Nothing in the verdict is
computed here; this script only groups the run directories by campaign (attempts in the
order they ran) and writes the verdict and a per-campaign summary as JSON.

    python3 -B analyze_controls.py EXPORT RUNS ATTEMPTS.json {C1,C2,C3} OUT_DIR

ATTEMPTS.json maps each campaign id to its job ids in attempt order (first, then rerun).
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
from typing import Any


def sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main() -> int:
    export, runs, attempts_path, criterion, out_dir = sys.argv[1:6]
    sys.path.insert(0, export)
    from harness.q2.action_path import acceptance as acc

    with open(attempts_path, encoding="utf-8") as handle:
        attempts: dict[str, list[str]] = json.load(handle)

    def load(jobs: list[str]) -> dict[str, Any]:
        earlier = [acc.load(os.path.join(runs, job)) for job in jobs[:-1]]
        return acc.load(os.path.join(runs, jobs[-1]), earlier=earlier)

    campaigns = {}
    for campaign_id, jobs in attempts.items():
        c = load(jobs)
        workload = c["manifest"].get("workload") or {}
        if workload.get("criterion") != criterion:
            continue
        if c["manifest"].get("campaign_id") != campaign_id:
            ran = c["manifest"].get("campaign_id")
            raise SystemExit(f"{campaign_id}: job {jobs[-1]} ran {ran}")
        campaigns[campaign_id] = c

    if criterion == "C2":
        verdict = acc.c2(list(campaigns.values()))
    elif criterion == "C1":
        by_layer: dict[str, list[dict[str, Any]]] = {}
        for c in campaigns.values():
            by_layer.setdefault(c["manifest"]["workload"]["layer"], []).append(c)
        verdict = acc.c1(by_layer)
    elif criterion == "C3":
        mutants: dict[tuple[str, str], list[dict[str, Any]]] = {}
        references: dict[str, list[dict[str, Any]]] = {}
        for c in campaigns.values():
            w = c["manifest"]["workload"]
            if w["mutant"] == "none":
                references.setdefault(w["layer"], []).append(c)
            else:
                mutants.setdefault((w["mutant"], w["layer"]), []).append(c)
        verdict = acc.c3(mutants, references)
    else:
        raise SystemExit(f"unknown criterion {criterion}")

    def summary(campaign_id: str, c: dict[str, Any]) -> dict[str, Any]:
        receipt = c["receipt"]
        trials = [(s, t) for s in c["sessions"] for t in s["trials"]]
        steps = [x for _, t in trials for x in t["steps_s"]]
        infra = collections.Counter(k for _, t in trials for k in t["infra"])
        retried = collections.Counter(k for _, t in trials for k in t["retried"])
        w = c["manifest"]["workload"]
        return {
            "campaign_id": campaign_id,
            "criterion": w.get("criterion"),
            "layer": w.get("layer"),
            "mutant": w.get("mutant"),
            "jobs": attempts[campaign_id],
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
            "unreadable": c["unreadable"],
            "receipt_sha256": sha256(os.path.join(c["run_dir"], "receipt.json")),
            "manifest_json_sha256": sha256(os.path.join(c["run_dir"], "manifest.json")),
            "sessions": len(c["sessions"]),
            "trials": len(trials),
            "trials_pass": sum(1 for _, t in trials if t["pass"]),
            "failed_trials": [
                {
                    "cycle": s.get("cycle"),
                    "setting": s["setting"],
                    "seq": t["seq"],
                    "cell": t["cell"],
                    "infra": t["infra"],
                    "reasons": t["reasons"],
                }
                for s, t in trials
                if not t["pass"]
            ],
            "infra_types": dict(infra),
            "observation_retries": dict(retried),
            "reset_observations": [s.get("reset_observation") for s in c["sessions"]],
            "session_errors": [s.get("error") for s in c["sessions"] if s.get("error")],
            "boot_s": [s.get("boot_s") for s in c["sessions"]],
            "step_s": {
                "n": len(steps),
                "p50": acc.quantile(steps, 0.5),
                "p95": acc.quantile(steps, 0.95),
            },
            "restarts": sum(s.get("restarts") or 0 for s in c["sessions"]),
        }

    os.makedirs(out_dir, exist_ok=True)
    tag = criterion.lower()
    with open(os.path.join(out_dir, f"{tag}-verdict.json"), "w", encoding="utf-8") as handle:
        json.dump(verdict, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    with open(os.path.join(out_dir, f"{tag}-campaigns.json"), "w", encoding="utf-8") as handle:
        json.dump(
            [summary(k, c) for k, c in sorted(campaigns.items())],
            handle,
            indent=2,
            sort_keys=True,
            default=str,
        )
        handle.write("\n")
    print(json.dumps({"criterion": criterion, "pass": verdict["pass"],
                      "problems": verdict["problems"], "campaigns": len(campaigns)}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
