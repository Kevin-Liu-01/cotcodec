#!/usr/bin/env python3
"""Fixed run command for the OpenResearch (orx) experiment tree.

orx requires one run command shared by every node; nodes differ only in
committed code. This dispatcher reads the committed ``experiments/orx/node.yaml``
on the node's branch and runs exactly one of two kinds of work:

* ``kind: cpu-doctor`` — a registered CPU phase-0 doctor
  (``scripts/run_*_doctor.py``), model-free, from this checkout;
* ``kind: slurm-manifest`` — a discovery-lane H100 manifest submitted ONLY
  through ``scripts/submit_docker_research_job.py`` (dry-run, test-only, then
  submit), then polled to completion with the Slurm output echoed to stdout.

orx captures stdout as the run's evidence, so the dispatcher prints the node
contract, the exact argv, the receipt summary, and a final status line. It never
launches provider CLIs, raw ``sbatch``, or training commands directly, and it
never edits the repository: the admission gates stay in the scripts it calls.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NODE_PATH = PROJECT_ROOT / "experiments" / "orx" / "node.yaml"
DOCTOR_PREFIX = "scripts/run_"
DOCTOR_SUFFIX = "_doctor.py"
SUBMITTER = "scripts/submit_docker_research_job.py"
KINDS = {"cpu-doctor", "slurm-manifest"}


class NodeContractError(ValueError):
    """Raised when node.yaml does not describe an admissible run."""


def load_node(path: Path = NODE_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise NodeContractError(f"missing node contract: {path}")
    node = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(node, dict):
        raise NodeContractError("node.yaml must be a mapping")
    kind = node.get("kind")
    if kind not in KINDS:
        raise NodeContractError(f"kind must be one of {sorted(KINDS)}, got {kind!r}")
    direction = node.get("direction")
    if not isinstance(direction, str) or not direction.strip():
        raise NodeContractError("direction must name the research direction")
    if kind == "cpu-doctor":
        doctor = node.get("doctor")
        if (
            not isinstance(doctor, str)
            or not doctor.startswith(DOCTOR_PREFIX)
            or not doctor.endswith(DOCTOR_SUFFIX)
            or "/" in doctor[len(DOCTOR_PREFIX) :]
        ):
            raise NodeContractError("doctor must be scripts/run_<name>_doctor.py")
        if not (PROJECT_ROOT / doctor).is_file():
            raise NodeContractError(f"doctor script does not exist: {doctor}")
        args = node.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise NodeContractError("args must be a list of strings")
        if any(a in {"--output", "-o"} or a.startswith("--output=") for a in args):
            raise NodeContractError("args must not set --output; the dispatcher owns it")
    else:
        manifest = node.get("manifest")
        if not isinstance(manifest, str) or not manifest.startswith("experiments/"):
            raise NodeContractError("manifest must be a committed experiments/ YAML path")
        if not manifest.endswith(".yaml") or not (PROJECT_ROOT / manifest).is_file():
            raise NodeContractError(f"manifest does not exist: {manifest}")
        if not (PROJECT_ROOT / SUBMITTER).is_file():
            raise NodeContractError(f"submitter missing: {SUBMITTER}")
    return node


def doctor_argv(node: dict[str, Any], output: Path) -> list[str]:
    return [
        sys.executable,
        str(PROJECT_ROOT / node["doctor"]),
        *node.get("args", []),
        "--output",
        str(output),
    ]


def submitter_argv(node: dict[str, Any], stage: str) -> list[str]:
    argv = [sys.executable, str(PROJECT_ROOT / SUBMITTER), str(PROJECT_ROOT / node["manifest"])]
    if stage in {"--dry-run", "--test-only"}:
        argv.append(stage)
    return argv


def summarize_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """A compact, stable subset of a doctor receipt for the run log."""
    summary: dict[str, Any] = {}
    for key in ("doctor", "status", "evidence_grade", "elapsed_seconds"):
        if key in receipt:
            summary[key] = receipt[key]
    cases = receipt.get("cases")
    entries: list[Any] = []
    if isinstance(cases, list):
        entries = cases
    elif isinstance(cases, dict):
        entries = list(cases.values())
    if entries:
        passed = sum(1 for c in entries if case_passed(c))
        summary["cases"] = {"total": len(entries), "passed": passed}
    return summary


def case_passed(case: Any) -> bool:
    """Doctors report a case as ``passed: true`` or ``status: PASS``; accept both."""
    if isinstance(case, str):
        return case.upper() == "PASS"
    if not isinstance(case, dict):
        return False
    if case.get("passed") is True:
        return True
    status = case.get("status")
    return isinstance(status, str) and status.upper() == "PASS"


def run_cpu_doctor(node: dict[str, Any], out_dir: Path, run_id: str) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{node['direction']}-orx-{run_id}.json"
    argv = doctor_argv(node, output)
    print("ORX_NODE", json.dumps(node, sort_keys=True))
    print("ORX_ARGV", shlex.join(argv), flush=True)
    code = subprocess.call(argv, cwd=PROJECT_ROOT)
    if output.is_file():
        receipt = json.loads(output.read_text(encoding="utf-8"))
        print("ORX_RECEIPT_SUMMARY", json.dumps(summarize_receipt(receipt), sort_keys=True))
        print("ORX_RECEIPT_PATH", output)
    else:
        print("ORX_RECEIPT_MISSING", output)
        code = code or 3
    print(f"ORX_RESULT kind=cpu-doctor direction={node['direction']} exit={code}", flush=True)
    return code


def parse_job_id(stdout: str) -> str | None:
    for line in stdout.splitlines():
        token = line.strip().split()[-1] if line.strip() else ""
        if token.isdigit():
            return token
    return None


def squeue_state(job_id: str) -> str:
    out = subprocess.run(
        ["squeue", "-h", "-j", job_id, "-o", "%T"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip()


def parse_slurm_terminal(stdout: str) -> tuple[str, str]:
    """Extract the terminal scheduler state and exit code from ``scontrol -o``."""

    fields = {}
    for token in stdout.split():
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value
    return fields.get("JobState", "UNKNOWN"), fields.get("ExitCode", "UNKNOWN")


def slurm_terminal(job_id: str) -> tuple[str, str]:
    completed = subprocess.run(
        ["scontrol", "show", "job", "-o", job_id],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "UNAVAILABLE", "UNAVAILABLE"
    return parse_slurm_terminal(completed.stdout)


def slurm_succeeded(state: str, exit_code: str) -> bool:
    return state == "COMPLETED" and exit_code == "0:0"


def run_slurm_manifest(node: dict[str, Any], poll_seconds: int) -> int:
    print("ORX_NODE", json.dumps(node, sort_keys=True), flush=True)
    for stage in ("--dry-run", "--test-only"):
        argv = submitter_argv(node, stage)
        print("ORX_ARGV", shlex.join(argv), flush=True)
        code = subprocess.call(argv, cwd=PROJECT_ROOT)
        if code != 0:
            print(f"ORX_RESULT kind=slurm-manifest stage={stage} exit={code}", flush=True)
            return code
    argv = submitter_argv(node, "submit")
    print("ORX_ARGV", shlex.join(argv), flush=True)
    submitted = subprocess.run(argv, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    print(submitted.stdout, end="")
    print(submitted.stderr, end="", file=sys.stderr)
    if submitted.returncode != 0:
        print(
            f"ORX_RESULT kind=slurm-manifest stage=submit exit={submitted.returncode}", flush=True
        )
        return submitted.returncode
    job_id = parse_job_id(submitted.stdout)
    if job_id is None:
        print("ORX_RESULT kind=slurm-manifest stage=submit exit=4 reason=no-job-id", flush=True)
        return 4
    print(f"ORX_SLURM_JOB {job_id}", flush=True)
    while True:
        state = squeue_state(job_id)
        if not state:
            break
        print(f"ORX_SLURM_STATE {job_id} {state}", flush=True)
        time.sleep(poll_seconds)
    terminal_state, exit_code = slurm_terminal(job_id)
    print(
        f"ORX_SLURM_TERMINAL {job_id} state={terminal_state} exit_code={exit_code}",
        flush=True,
    )
    if not slurm_succeeded(terminal_state, exit_code):
        print(
            f"ORX_RESULT kind=slurm-manifest direction={node['direction']} "
            f"job={job_id} exit=5",
            flush=True,
        )
        return 5
    print(
        f"ORX_RESULT kind=slurm-manifest direction={node['direction']} job={job_id} exit=0",
        flush=True,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", type=Path, default=NODE_PATH)
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "data" / "results" / "orx")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true", help="validate and print the plan only")
    args = parser.parse_args(argv)
    try:
        node = load_node(args.node)
    except NodeContractError as exc:
        print(f"ORX_NODE_INVALID {exc}", file=sys.stderr)
        return 2
    run_id = os.environ.get("ORX_RUN_ID", "local")
    if args.dry_run:
        plan = (
            doctor_argv(node, args.out_dir / f"{node['direction']}-orx-{run_id}.json")
            if node["kind"] == "cpu-doctor"
            else submitter_argv(node, "--dry-run")
        )
        print(
            json.dumps(
                {"node": node, "plan_argv": plan, "run_id": run_id}, indent=2, sort_keys=True
            )
        )
        return 0
    if node["kind"] == "cpu-doctor":
        return run_cpu_doctor(node, args.out_dir, run_id)
    return run_slurm_manifest(node, args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
