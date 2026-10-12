#!/usr/bin/env python3
"""Render the lane manifest of an E VM job, or the GPU half of its pair, from E's plan.

q2-stage1-successor-e-v1 sections 5-6. Every E job's slots come from
``harness.q2_stage1e.plan.slots``, never from a hand-written list, and
``harness.q2_stage1e.lane.validate_manifest`` refuses a manifest whose slots differ:

* ``vm --plan PLAN --size Z --session S --prior-run-dirs D...``: one E job from E's plan
  file (a path inside the source tree whose digest the registration states).
  ``--prior-run-dirs`` names the lane run directory of every earlier E job in the registered
  order (``plan.job_order``: E1 to E4, each 9B then 4B); the manifest carries each one's
  record file and receipt by SHA-256, and the lane refuses the job if one is missing or fired
  DR0. A job of E2-E4 may not start before the previous session's later job ended plus 12 h
  and 5 minutes;
* ``vm --development --tasks T... --name N``: the pre-freeze development smoke (CPU only,
  the scripted fake engine of ``--fake-script``, dev-split tasks under both harnesses, E's
  record labels, session E1);
* ``gpu --vm-manifest M --vm-job-id ID --values V``: S1a's GPU template
  (``experiments/manifests/q2-stage1/gpu-engine.template.yaml``), filled by S1a's
  ``render_q2_stage1_manifest.gpu_manifest`` for the validated E VM manifest's size and cap
  (never from the command line).

The host-specific inputs come from ``--host`` (S1a's host JSON). Nothing is submitted;
outputs are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import render_q2_stage1_manifest as S1A  # noqa: E402

from harness.q2_stage1 import lane as L1  # noqa: E402
from harness.q2_stage1 import plan as P1  # noqa: E402
from harness.q2_stage1e import lane as LE  # noqa: E402
from harness.q2_stage1e import plan as PE  # noqa: E402

GPU_TEMPLATE = S1A.GPU_TEMPLATE
HOST_KEYS = S1A.HOST_KEYS


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _host(host: Mapping[str, Any]) -> None:
    missing = [k for k in HOST_KEYS if k not in host]
    if missing:
        raise ValueError(f"--host lacks {missing}")
    fixed = sorted(set(host) & {"episode_image_id", *L1.FIXED_KEYS})
    if fixed:
        raise ValueError(f"--host may not set {fixed}: the registration fixes them")


def prior_jobs(job: str, run_dirs: Sequence[Path]) -> list[dict[str, Any]]:
    """Every E job before ``job`` in the registered order, from their lane run directories."""
    found: dict[str, Path] = {}
    for run_dir in run_dirs:
        m = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))
        e = m.get("e") or {}
        name = PE.job_name(str(e.get("size")), str(e.get("session")))
        if m.get("purpose") != "e" or name in found:
            raise ValueError(f"{run_dir} is not one distinct E job's run directory")
        found[name] = Path(run_dir)
    order = PE.job_order()
    earlier = order[: order.index(job)]
    if sorted(found) != sorted(earlier):
        raise ValueError(f"{job} needs the run directories of {earlier}, got {sorted(found)}")
    out = []
    for name in earlier:
        records, receipt = found[name] / "episodes.jsonl", found[name] / "lane-receipt.json"
        out.append({
            "job": name,
            "records": {"path": str(records), "sha256": sha256_file(records)},
            "receipt": {"path": str(receipt), "sha256": sha256_file(receipt)},
        })  # fmt: skip
    return out


def vm_manifest(
    *,
    host: Mapping[str, Any],
    source_dir: Path,
    plan_path: str,
    size: str,
    session: str,
    prior_run_dirs: Sequence[Path] = (),
) -> dict[str, Any]:
    """The lane manifest of one E job."""
    _host(host)
    data = PE.load_plan(Path(source_dir) / plan_path)
    job = PE.job_name(size, session)
    cap = int(data["caps_minutes"][f"E-{size}"])
    v = int(data["V"])
    return {
        "schema": LE.SCHEMA,
        "experiment_id": LE.EXPERIMENT_ID,
        "purpose": "e",
        "name": host.get("name", job.lower()),
        "run_root": host["run_root"],
        "vm": {**host["vm"], "concurrency": v},
        "episode_image_id": L1.EPISODE_IMAGE_ID,
        "osworld": host["osworld"],
        "file_cache": host["file_cache"],
        "engine": {**host["engine"], "kind": "bridge", "gpu_cap_min": cap},
        "mode": "episode",
        "date": P1.PROMPT_DATE,
        "slots": PE.slots(data, size, session),
        "slurm": {
            "cpus": P1.vm_job_cpus(v),
            "memory_gb": int(host.get("memory_gb", 6 * v + 6)),
            "minutes": cap + P1.VM_JOB_EXTRA_MIN,
        },
        "plan": {"path": plan_path, "sha256": data["plan_sha256"]},
        "e": {"size": size, "session": session, "prior_jobs": prior_jobs(job, prior_run_dirs)},
    }


def development_manifest(
    *,
    host: Mapping[str, Any],
    source_dir: Path,
    tasks: Sequence[str],
    script: Mapping[str, Any],
    name: str,
) -> dict[str, Any]:
    """The pre-freeze development smoke: the fake engine, one VM at a time, the given dev
    tasks under both harnesses, E's labels (session E1, rerun 1), 9B's slot labels."""
    _host({**host, "engine": host.get("engine", {})})
    dev = LE.dev_tasks(Path(source_dir))
    unknown = [t for t in tasks if t not in dev]
    if unknown:
        raise ValueError(f"not dev-split tasks: {unknown}")
    cells = [(t, h) for t in tasks for h in PE.HARNESSES]
    slots = P1.block_slots("E-dev", "9B", PE.SESSIONS[0], "dev", PE.RERUN, cells)
    return {
        "schema": LE.SCHEMA,
        "experiment_id": LE.EXPERIMENT_ID,
        "purpose": "development",
        "name": name,
        "note": "Development smoke of E's lane and episode entry point with the scripted fake "
                "engine (no model, no GPU) on dev-split tasks. Never evidence for any estimand.",
        "run_root": host["run_root"],
        "vm": {**host["vm"], "concurrency": 1},
        "episode_image_id": L1.EPISODE_IMAGE_ID,
        "osworld": host["osworld"],
        "file_cache": host["file_cache"],
        "engine": {"kind": "fake", "script": dict(script)},
        "mode": "episode",
        "date": P1.PROMPT_DATE,
        "slots": slots,
        "slurm": {"cpus": 8, "memory_gb": 16, "minutes": 60},
    }  # fmt: skip


def gpu_for_vm_manifest(
    template: str, vm: Mapping[str, Any], *, vm_job_id: str, values: Mapping[str, str]
) -> str:
    """The GPU half of an E pair from its validated VM manifest: its size, its cap."""
    if vm.get("purpose") != "e":
        raise ValueError("the GPU half belongs to an E job")
    size = str((vm.get("e") or {}).get("size"))
    minutes = int(vm["engine"]["gpu_cap_min"])
    return S1A.gpu_manifest(template, size=size, minutes=minutes, vm_job_id=vm_job_id,
                            values=values)  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    vm = sub.add_parser("vm", help="an E job's lane manifest, or the development smoke's")
    vm.add_argument("--host", type=Path, required=True)
    vm.add_argument("--source-dir", type=Path, default=PROJECT_ROOT)
    vm.add_argument("--plan", default=PE.PLAN_FILE, help="E's plan file, relative to the tree")
    vm.add_argument("--size", choices=PE.SIZES)
    vm.add_argument("--session", choices=PE.SESSIONS)
    vm.add_argument("--prior-run-dirs", type=Path, nargs="*", default=[])
    vm.add_argument("--development", action="store_true")
    vm.add_argument("--tasks", nargs="*", default=[])
    vm.add_argument("--fake-script", type=Path)
    vm.add_argument("--name", default="e-dev-smoke-v1")
    vm.add_argument("--out", type=Path, required=True)
    gpu = sub.add_parser("gpu", help="the GPU half of an E pair, from its VM manifest")
    gpu.add_argument("--vm-manifest", type=Path, required=True)
    gpu.add_argument("--source-dir", type=Path, default=PROJECT_ROOT)
    gpu.add_argument("--vm-job-id", required=True)
    gpu.add_argument("--values", type=Path, required=True)
    gpu.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; manifests are never overwritten")
    if args.command == "gpu":
        template = (PROJECT_ROOT / GPU_TEMPLATE).read_text(encoding="utf-8")
        values = json.loads(args.values.read_text(encoding="utf-8"))
        vm_m = LE.validate_manifest(
            json.loads(args.vm_manifest.read_text(encoding="utf-8")), args.source_dir
        )
        text = gpu_for_vm_manifest(template, vm_m, vm_job_id=args.vm_job_id, values=values)
        args.out.write_text(text, encoding="utf-8")
        print(hashlib.sha256(text.encode()).hexdigest())
        return 0
    host = json.loads(args.host.read_text(encoding="utf-8"))
    if args.development:
        if not (args.tasks and args.fake_script):
            raise SystemExit("--development needs --tasks and --fake-script")
        manifest = development_manifest(
            host=host, source_dir=args.source_dir, tasks=args.tasks, name=args.name,
            script=json.loads(args.fake_script.read_text(encoding="utf-8")),
        )  # fmt: skip
    else:
        if not (args.size and args.session):
            raise SystemExit("an E job needs --size and --session")
        manifest = vm_manifest(
            host=host, source_dir=args.source_dir, plan_path=args.plan, size=args.size,
            session=args.session, prior_run_dirs=args.prior_run_dirs,
        )  # fmt: skip
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(hashlib.sha256(text.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
