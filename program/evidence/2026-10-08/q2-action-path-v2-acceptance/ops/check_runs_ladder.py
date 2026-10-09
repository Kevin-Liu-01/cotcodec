#!/usr/bin/env python3
"""Operator checks of every q2-action-path-v2 ladder run against what was submitted.

``check_runs_acceptance.py`` with the ladder's registered shape (section 9). For each job in
``ops/submissions.log`` whose label starts with ``ladder-``: the run's ``manifest.json``
equals the rendered manifest it was submitted from (``manifests/rendered/``) and its
canonical digest equals ``manifest_sha256`` in the batch record; the batch record names the
frozen batch script and the export's tree digest; the receipt names the same job, campaign,
git SHA, tree, manifest and session plan, started after the executor addendum's ledger row,
reports no GPU, an unchanged ``System.qcow2`` and nothing left; the Slurm record (the
watcher's ``scontrol show job``) is COMPLETED 0:0 with no GPU in its TRES, runs the export's
batch script and was never requeued (``Restarts=0``); and the rung has its registered shape:
L0-fixed, seed 43, both settings, attempt 1, ``manifest.ladder_reps(N)`` repetitions,
``manifest.runner_cpus(N)`` runner CPUs, N x 4 vCPUs at most 160, every VM's cpuset inside
the job's allocation, and the Slurm CPUs N x 4 plus the runner's. It also lists every IPv4
address in the files it reads. It judges nothing (``acceptance.py`` does); it checks that the
evidence is what ran.

    python3 -B check_runs_ladder.py EVIDENCE_DIR > checks/run-checks-ladder.json
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any

import yaml

BATCH_SHA256 = "3d86820d176e3a9f0699814a19f62154cde00f88da1777a33c804e884288ac8a"
TREE_SHA256 = "abbbfe6cb74c4573856ac1e6cd906f8332f48836e636c53aac4c65fa634dbf23"
GIT_SHA = "bf99a645c3782b2c59a75b6f463461b2515d0d97"
EXECUTOR_FROZEN_AT = "2026-10-08T14:23:49.399774+00:00"
EXPORT = f"/home/kevin/cotcodec-runs/q2-action-path-v2/src/{GIT_SHA}"
BATCH = "infra/slurm/host-single-node/vm-campaign.sbatch"
BOTH = ["screenshot", "screenshot+a11y"]
# Section 9: rung N -> (r_N, sessions, trials, runner CPUs).
RUNGS = {
    8: (6, 20, 1200, 4),
    16: (10, 34, 2000, 8),
    24: (14, 48, 2800, 12),
    32: (19, 64, 3800, 16),
    40: (24, 80, 4800, 20),
}
IPV4 = re.compile(rb"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def cpus(text: str) -> set[int]:
    out: set[int] = set()
    for part in str(text).split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part.strip():
            out.add(int(part))
    return out


def main() -> int:
    here = sys.argv[1]
    frozen = datetime.fromisoformat(EXECUTOR_FROZEN_AT).timestamp()
    line_re = re.compile(r"^(\S+) (\S+) job=(\d+) manifest=(\S+)$")
    rows, problems, read_paths = [], [], []
    lines = [
        line_re.match(line.strip())
        for line in read(os.path.join(here, "ops", "submissions.log")).splitlines()
        if line.strip()
    ]
    for match in lines:
        submitted, label, job, file = match.groups()
        if not label.startswith("ladder-"):
            continue
        run = os.path.join(here, "runs", job)
        paths = {
            "rendered": os.path.join(here, "manifests", "rendered", file),
            "manifest": os.path.join(run, "manifest.json"),
            "receipt": os.path.join(run, "receipt.json"),
            "preflight": os.path.join(run, "preflight.txt"),
            "plan": os.path.join(run, "session_plan.json"),
            "slurm": os.path.join(here, "slurm-state", f"{job}.txt"),
        }
        read_paths += paths.values()
        rendered = yaml.safe_load(read(paths["rendered"]))
        manifest = json.loads(read(paths["manifest"]))
        receipt = json.loads(read(paths["receipt"]))
        plan = json.loads(read(paths["plan"]))
        batch_record = read(paths["preflight"])
        preflight = dict(
            line.split("=", 1)
            for line in batch_record.splitlines()
            if "=" in line and not line.startswith("driver_exit")
        )
        slurm = read(paths["slurm"])
        tres = re.search(r"\bTRES=(\S+)", slurm).group(1)
        workload = manifest["workload"]
        n = manifest["vm"]["concurrency"]
        reps, sessions, trials, runner = RUNGS.get(n, (None, None, None, None))
        cores = manifest["vm"]["cpu_cores"]
        # driver.plan_cpusets_multi: one entry per concurrent VM, each naming the job's
        # allocation, the VM's own CPU set and the runners' shared set.
        sets = receipt.get("cpusets") or []
        sets = sets if isinstance(sets, list) else [sets]
        allocated = set().union(*(cpus(s.get("allocated", "")) for s in sets)) if sets else set()
        vm_cpus = [cpus(s.get("vm", "")) for s in sets if s.get("vm")]
        runner_sets = {s.get("runner") for s in sets}
        checks = {
            "manifest_equals_rendered": manifest == rendered,
            "manifest_digest_in_batch_record": preflight.get("manifest_sha256")
            == sha(canonical(manifest)),
            "batch_script_frozen": preflight.get("batch_sha256") == BATCH_SHA256,
            "tree_digest": preflight.get("source_tree_sha256")
            == TREE_SHA256
            == manifest["source"]["tree_sha256"]
            == receipt.get("source_tree_sha256"),
            "git_sha": manifest["git_sha"] == GIT_SHA == receipt.get("git_sha"),
            "receipt_job": str(receipt.get("job_id")) == job == preflight.get("job_id"),
            "receipt_campaign": receipt.get("campaign_id") == manifest["campaign_id"],
            "receipt_manifest_digest": receipt.get("manifest_sha256")
            == preflight.get("manifest_sha256"),
            "session_plan_digest": receipt.get("session_plan_sha256") == sha(canonical(plan)),
            "started_after_freeze": float(receipt.get("started_at") or 0) > frozen,
            "no_gpu": (receipt.get("summary") or {}).get("no_gpu_all") is True
            and "gpu" not in tres.lower()
            and "gres" not in tres.lower(),
            "qcow2_unchanged": receipt.get("qcow2_unchanged") is True,
            "nothing_left": receipt.get("labelled_containers_left") == []
            and (receipt.get("summary") or {}).get("leaked_volumes") == [],
            "slurm_completed": "JobState=COMPLETED" in slurm and "ExitCode=0:0" in slurm,
            "slurm_never_requeued": "Restarts=0" in slurm,
            "slurm_runs_export_batch": f"Command={EXPORT}/{BATCH}" in slurm,
            "batch_end": "driver_exit=0 labelled_containers_left=0" in batch_record,
            "label": label in ("ladder-attempt1", "ladder-rerun"),
            "rung": n in RUNGS,
            "criterion": workload["criterion"] == "ladder",
            "layer": workload["layer"] == "L0-fixed",
            "seed_43": manifest["randomness"]["seeds"] == [43],
            "settings": workload["settings"] == BOTH,
            "attempt_1": workload["attempt"] == 1,
            "no_mutant_no_range": workload["mutant"] is None and workload["session_range"] is None,
            "reps": workload["reps"] == reps,
            "sessions_and_trials": (workload["sessions"], workload["trials"]) == (sessions, trials),
            "runner_cpus": manifest["runner"]["cpus"] == runner,
            "vcpus_at_most_160": n * cores <= 160,
            "slurm_cpus": manifest["slurm"]["cpus"] == n * cores + (runner or 0),
            "one_cpuset_per_vm": len(vm_cpus) == n and all(len(v) == cores for v in vm_cpus),
            "vm_cpusets_disjoint": len(set().union(*vm_cpus)) == n * cores if vm_cpus else False,
            "vm_cpusets_inside_allocation": bool(vm_cpus) and all(v <= allocated for v in vm_cpus),
            "runner_cpuset_shared_and_apart": len(runner_sets) == 1
            and len(cpus(next(iter(runner_sets)) or "")) == runner
            and not (cpus(next(iter(runner_sets)) or "") & set().union(*vm_cpus)),
            "allocation_size": len(allocated) >= n * cores + (runner or 0),
        }
        bad = sorted(k for k, ok in checks.items() if not ok)
        if bad:
            problems.append(f"job {job}: {bad}")
        rows.append(
            {
                "job": job,
                "label": label,
                "submitted": submitted,
                "campaign_id": manifest["campaign_id"],
                "n": n,
                "reps": workload["reps"],
                "trials": workload["trials"],
                "sessions": workload["sessions"],
                "tres": tres,
                "run_time": re.search(r"\bRunTime=(\S+)", slurm).group(1),
                "requeue_restarts": re.search(r"\bRestarts=(\d+)", slurm).group(1),
                "started_at": datetime.fromtimestamp(
                    float(receipt["started_at"]), tz=UTC
                ).isoformat(timespec="seconds"),
                "finished_at": datetime.fromtimestamp(
                    float(receipt["finished_at"]), tz=UTC
                ).isoformat(timespec="seconds"),
                "cpusets": sets,
                "failed_checks": bad,
            }
        )
    addresses: dict[str, int] = {}
    for path in read_paths:
        with open(path, "rb") as handle:
            for found in IPV4.findall(handle.read()):
                addresses[found.decode()] = addresses.get(found.decode(), 0) + 1
    json.dump(
        {
            "jobs": len(rows),
            "problems": problems,
            "ipv4_addresses_in_files_read": addresses,
            "runs": rows,
        },
        sys.stdout,
        indent=1,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
