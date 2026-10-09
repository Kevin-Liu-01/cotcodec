#!/usr/bin/env python3
"""Operator checks of every q2-action-path-v2 acceptance run (N = 1 stage) against what was
submitted.

``check_runs.py`` (the validity controls) with each acceptance campaign's registered shape.
For each job in ``ops/submissions.log`` whose label starts with ``A``: the run's
``manifest.json`` equals the rendered manifest it was submitted from
(``manifests/rendered/``) and its canonical digest equals ``manifest_sha256`` in the batch
record; the batch record names the frozen batch script and the export's tree digest; the
receipt names the same job, campaign, git SHA, tree and manifest (and, for a suite or canary
campaign, the session plan: ``session_plan.json``'s canonical digest), started after the
executor addendum's ledger row, reports no GPU, an unchanged ``System.qcow2`` and nothing
left; the Slurm record (the watcher's ``scontrol show job``) is COMPLETED 0:0 with no GPU in
its TRES and runs the export's batch script; and the campaign has its registered shape
(N = 1, attempt 1, seed, layer, settings, repetitions). It also lists every IPv4 address in
the files it reads. It judges no criterion (``acceptance.py`` does); it checks that the
evidence is what ran.

    python3 -B check_runs_acceptance.py EVIDENCE_DIR > checks/run-checks-acceptance.json
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
# Registered shape per campaign id: (criterion, seeds, layer, settings, reps).
SHAPES = {
    "q2ap-v2-a5-bootreset-a1": ("A5", [], None, None, None),
    "q2ap-v2-a1-l0fixed-s43-a1": ("A1", [43], "L0-fixed", BOTH, 5),
    "q2ap-v2-a1-l0fixed-s44-a1": ("A1", [44], "L0-fixed", BOTH, 5),
    "q2ap-v2-a2-hoswfixed-a1": ("A2", [43], "H-OSW-fixed", BOTH, 5),
    "q2ap-v2-a2-hga-a1": ("A2", [43], "H-GA", BOTH, 5),
    "q2ap-v2-a3-l0fixed-a1": ("A3", [43], "L0-fixed", BOTH, 30),
    "q2ap-v2-a3-hoswfixed-a1": ("A3", [43], "H-OSW-fixed", BOTH, 30),
    "q2ap-v2-a3-hga-a1": ("A3", [43], "H-GA", BOTH, 30),
    "q2ap-v2-a6-canary-a1": ("A6", [43], None, None, 5),
}
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
    rows, problems, read_paths = [], [], []
    lines = [
        line_re.match(line.strip())
        for line in read(os.path.join(here, "ops", "submissions.log")).splitlines()
        if line.strip()
    ]
    for match in lines:
        submitted, label, job, file = match.groups()
        if not label.startswith("A"):
            continue
        run = os.path.join(here, "runs", job)
        paths = {
            "rendered": os.path.join(here, "manifests", "rendered", file),
            "manifest": os.path.join(run, "manifest.json"),
            "receipt": os.path.join(run, "receipt.json"),
            "preflight": os.path.join(run, "preflight.txt"),
            "slurm": os.path.join(here, "slurm-state", f"{job}.txt"),
        }
        read_paths += paths.values()
        rendered = yaml.safe_load(read(paths["rendered"]))
        manifest = json.loads(read(paths["manifest"]))
        receipt = json.loads(read(paths["receipt"]))
        batch_record = read(paths["preflight"])
        preflight = dict(
            line.split("=", 1)
            for line in batch_record.splitlines()
            if "=" in line and not line.startswith("driver_exit")
        )
        slurm = read(paths["slurm"])
        tres = re.search(r"\bTRES=(\S+)", slurm).group(1)
        workload = manifest["workload"]
        criterion, seeds, layer, settings, reps = SHAPES[manifest["campaign_id"]]
        plan_path = os.path.join(run, "session_plan.json")
        if criterion == "A5":
            plan_ok = not os.path.exists(plan_path) and "session_plan_sha256" not in receipt
            shape = {
                "boot_reset_workload": workload["kind"] == "boot-reset-validation"
                and workload["cycles"] == 21,
                "infrastructure_validation": manifest["purpose"] == "infrastructure-validation",
                "deterministic": manifest["randomness"] == {"contract": "deterministic", "seeds": []},
            }
        else:
            read_paths.append(plan_path)
            plan = json.loads(read(plan_path))
            plan_ok = receipt.get("session_plan_sha256") == sha(canonical(plan))
            shape = {
                "attempt_1": workload["attempt"] == 1,
                "registered_seed": manifest["randomness"]["seeds"] == seeds,
                "registered_reps": workload["reps"] == reps,
            }
            if criterion == "A6":
                shape["canary_apps"] = workload["kind"] == "canary-acceptance" and workload[
                    "apps"
                ] == ["writer", "chrome", "vscode", "terminal"]
            else:
                shape["criterion"] = workload["criterion"] == criterion
                shape["layer"] = workload["layer"] == layer
                shape["settings"] = workload["settings"] == settings
                shape["no_mutant_no_range"] = (
                    workload["mutant"] is None and workload["session_range"] is None
                )
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
            "session_plan_digest": plan_ok,
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
            "label_matches_criterion": label == f"{criterion}-attempt1",
            **shape,
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
                "layer": layer,
                "trials": workload.get("trials"),
                "sessions": workload.get("sessions", workload.get("cycles")),
                "tres": tres,
                "run_time": re.search(r"\bRunTime=(\S+)", slurm).group(1),
                "started_at": datetime.fromtimestamp(
                    float(receipt["started_at"]), tz=UTC
                ).isoformat(timespec="seconds"),
                "finished_at": datetime.fromtimestamp(
                    float(receipt["finished_at"]), tz=UTC
                ).isoformat(timespec="seconds"),
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
