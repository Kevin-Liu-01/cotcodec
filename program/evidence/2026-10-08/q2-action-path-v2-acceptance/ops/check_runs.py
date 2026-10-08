#!/usr/bin/env python3
"""Operator checks of every q2-action-path-v2 validity-control run against what was submitted.

For each job in ``ops/submissions.log``: the run's ``manifest.json`` equals the rendered
manifest it was submitted from (``manifests/rendered/``) and its canonical digest equals
``manifest_sha256`` in the batch record; the batch record names the frozen batch script
and the export's tree digest; the receipt names the same job, campaign, git SHA, tree,
manifest and session plan (``session_plan.json``'s canonical digest), started after the
executor addendum's ledger row, reports no GPU, an unchanged ``System.qcow2`` and nothing
left; the Slurm record (the watcher's ``scontrol show job``) is COMPLETED 0:0 with no GPU
in its TRES and runs the export's batch script; and the campaign is N = 1, attempt 1, on
its registered seed. It also lists every IPv4 address in the evidence bundle. It judges no
criterion (``acceptance.py`` does); it checks that the evidence is what ran.

    python3 -B check_runs.py EVIDENCE_DIR > checks/run-checks.json
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
SEEDS = {"C1": 42, "C2": 45, "C3": 42}
IPV4 = re.compile(rb"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    here = sys.argv[1]
    frozen = datetime.fromisoformat(EXECUTOR_FROZEN_AT).timestamp()
    line_re = re.compile(r"^(\S+) (\S+) job=(\d+) manifest=(\S+)$")
    rows, problems = [], []
    lines = [
        line_re.match(line.strip())
        for line in read(os.path.join(here, "ops", "submissions.log")).splitlines()
        if line.strip()
    ]
    for match in lines:
        submitted, label, job, file = match.groups()
        run = os.path.join(here, "runs", job)
        rendered = yaml.safe_load(read(os.path.join(here, "manifests", "rendered", file)))
        manifest = json.loads(read(os.path.join(run, "manifest.json")))
        receipt = json.loads(read(os.path.join(run, "receipt.json")))
        plan = json.loads(read(os.path.join(run, "session_plan.json")))
        batch_record = read(os.path.join(run, "preflight.txt"))
        preflight = dict(
            line.split("=", 1)
            for line in batch_record.splitlines()
            if "=" in line and not line.startswith("driver_exit")
        )
        slurm = read(os.path.join(here, "slurm-state", f"{job}.txt"))
        tres = re.search(r"\bTRES=(\S+)", slurm).group(1)
        workload = manifest["workload"]
        criterion = workload["criterion"]
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
            "slurm_runs_export_batch": f"Command={EXPORT}/{BATCH}" in slurm,
            "batch_end": "driver_exit=0 labelled_containers_left=0" in batch_record,
            "n_equals_1": manifest["vm"]["concurrency"] == 1,
            "attempt_1": workload["attempt"] == 1,
            "registered_seed": manifest["randomness"]["seeds"] == [SEEDS[criterion]],
            "screenshot_setting": workload["settings"] == ["screenshot"],
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
                "criterion": criterion,
                "layer": workload["layer"],
                "mutant": workload["mutant"],
                "trials": workload["trials"],
                "sessions": workload["sessions"],
                "tres": tres,
                "run_time": re.search(r"\bRunTime=(\S+)", slurm).group(1),
                "started_at": datetime.fromtimestamp(
                    float(receipt["started_at"]), tz=UTC
                ).isoformat(timespec="seconds"),
                "failed_checks": bad,
            }
        )
    addresses: dict[str, int] = {}
    for dirpath, _, filenames in os.walk(here):
        for filename in filenames:
            with open(os.path.join(dirpath, filename), "rb") as handle:
                for found in IPV4.findall(handle.read()):
                    addresses[found.decode()] = addresses.get(found.decode(), 0) + 1
    json.dump(
        {
            "jobs": len(rows),
            "problems": problems,
            "ipv4_addresses_in_bundle": addresses,
            "runs": rows,
        },
        sys.stdout,
        indent=1,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
