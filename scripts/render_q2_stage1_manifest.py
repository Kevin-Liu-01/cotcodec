#!/usr/bin/env python3
"""Render the lane manifest of an S1a VM job, or the GPU half of its pair, from the plan.

q2-stage1-rescoped-v1 sections 5.4-5.6, 6.1 and 14. Every registered VM job's slots come
from ``harness.q2_stage1.plan`` (``a0a_slots``, ``a1_slots``), never from a hand-written
list, and ``lane.validate_manifest`` refuses a manifest whose slots or fill blocks differ
from what this script renders:

* ``vm --purpose a0a --n-star N``: A0a's V episodes (V = A1's V at N*), the dev tasks of
  the committed setup-check records, GPU cap 25 minutes;
* ``vm --purpose a1 --plan PLAN --size Z --session S --prior-run-dirs D...``: one A1 job
  from the frozen plan file (a path inside the source tree whose digest the frozen
  registration states). ``--prior-run-dirs`` names the lane run directory of every earlier
  A1 job in the registered order (``plan.a1_job_order``: 9B then 4B, session 1 then 2);
  the manifest carries each one's record file and receipt by SHA-256, and the lane refuses
  the job if one is missing or fired DR0. A session-1 job gets base blocks b1 and b2 and
  every extension block as fill blocks; a session-2 job gets its base blocks, then exactly
  the extension blocks both session-1 jobs completed, recomputed from their record files
  (``records.completed_extension_blocks(..., sessions=("S1",))``), and may not start
  before the later session-1 job's end plus 12 hours.

The host-specific inputs (VM pins and qcow2, OSWorld and file-cache directories, the run
root and the bridge directory template) come from ``--host``, a JSON object. The episode
image is the registered one (``lane.EPISODE_IMAGE_ID``); re-queue and the episode timeout
are the lane's and cannot be set. Every registered job pins the prompt date
(``plan.PROMPT_DATE``), takes ``plan.vm_job_cpus(V)`` CPUs and a limit of its GPU cap plus
10 minutes.

``gpu --vm-manifest M --vm-job-id ID --values V`` fills
``experiments/manifests/q2-stage1/gpu-engine.template.yaml`` (the engine and bridge job,
held by Slurm until its VM job starts) for the VM job ``M``: the size (A0a: 9B; A1: its
size) and the cap (A0a: 25 minutes; A1: the frozen T_A1) come from that validated manifest,
never from the command line. It refuses a slot left unfilled. Nothing is submitted; outputs
are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q2_stage1 import lane  # noqa: E402
from harness.q2_stage1 import plan as P  # noqa: E402

GPU_TEMPLATE = "experiments/manifests/q2-stage1/gpu-engine.template.yaml"
# Registration section 4: the served models (registry id, pinned revision).
MODELS = {
    "9B": ("qwen3.5-9b", "c202236235762e1c871ad0ccb60c8ee5ba337b9a"),
    "4B": ("qwen3.5-4b", "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"),
    "anchor": ("opencua-7b", "a2efb7d2b104d477a4a2666a357e79550a28aafc"),
}
HOST_KEYS = ("run_root", "vm", "osworld", "file_cache", "engine")
# The GPU template's host-specific slots; the size, model, revision, cap and budget are
# derived here and cannot be passed in.
HOST_FILLS = ("FILL_JOB", "FILL_OVERLAY_IMAGE_ID", "FILL_GIT_SHA", "FILL_SOURCE_SHA256",
              "FILL_RECEIPT_SHA256", "FILL_ARTIFACT_ROOT_SHA256")  # fmt: skip


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def vm_manifest(
    *,
    purpose: str,
    host: Mapping[str, Any],
    source_dir: Path,
    n_star: int | None = None,
    plan_path: str | None = None,
    size: str | None = None,
    session: str | None = None,
    prior_run_dirs: Sequence[Path] = (),
) -> dict[str, Any]:
    """The lane manifest of one registered VM job (A0a or one A1 job)."""
    missing = [k for k in HOST_KEYS if k not in host]
    if missing:
        raise ValueError(f"--host lacks {missing}")
    fixed = sorted(set(host) & {"episode_image_id", *lane.FIXED_KEYS})
    if fixed:
        raise ValueError(f"--host may not set {fixed}: the registration fixes them")
    extra: dict[str, Any] = {}
    fill = None
    if purpose == "a0a":
        if n_star is None:
            raise ValueError("A0a needs --n-star (the accepted attempt's ladder value)")
        v = P.a1_concurrency(n_star)
        if v is None:
            raise ValueError("N* < 16: S1a does not start")
        if n_star < P.A0A_MIN_NSTAR:
            raise ValueError("N* = 16: the draft goes back to review before A0a (section 5.5)")
        splits = json.loads((source_dir / lane.SPLITS).read_text(encoding="utf-8"))
        rows = P.load_setup_check(source_dir)
        slots = P.a0a_slots(splits["dev"], P.dev_setup_ok(rows), v)
        cap, name = P.CAP_MINUTES["A0a"], f"a0a-n{n_star}"
        extra["n_star"] = n_star
    elif purpose == "a1":
        if not (plan_path and size and session):
            raise ValueError("A1 needs --plan, --size and --session")
        data = json.loads((source_dir / plan_path).read_text(encoding="utf-8"))
        constants = data["constants"]
        v, cap = constants["a1_v"], constants["a1_cap_min"]
        a1: dict[str, Any] = {"size": size, "session": session}
        a1["prior_jobs"] = prior_jobs(P.a1_job(size, session), prior_run_dirs)
        s2_blocks = None
        if session == "S2":
            from harness.q2_stage1.records import completed_extension_blocks

            rows = [
                r
                for item in a1["prior_jobs"]
                if item["job"].endswith("-S1")
                for r in read_jsonl(Path(item["records"]["path"]))
            ]
            planned = {int(k): t for k, t in data["extension_blocks"].items()}
            s2_blocks = completed_extension_blocks(rows, planned, sessions=("S1",))
            a1["s2_extension_blocks"] = s2_blocks
        slots, fill = P.a1_slots(data, size, session, s2_blocks)
        name = f"a1-{size.lower()}-{session.lower()}"
        extra["plan"] = {"path": plan_path, "sha256": data["plan_sha256"]}
        extra["a1"] = a1
    else:
        raise ValueError("purpose must be a0a or a1 (the anchor is UNAVAILABLE)")
    manifest: dict[str, Any] = {
        "schema": lane.SCHEMA,
        "experiment_id": lane.EXPERIMENT_ID,
        "purpose": purpose,
        "name": host.get("name", name),
        "run_root": host["run_root"],
        "vm": {**host["vm"], "concurrency": v},
        "episode_image_id": lane.EPISODE_IMAGE_ID,
        "osworld": host["osworld"],
        "file_cache": host["file_cache"],
        "engine": {**host["engine"], "kind": "bridge", "gpu_cap_min": cap},
        "mode": "episode",
        "date": P.PROMPT_DATE,
        "slots": slots,
        "slurm": {
            "cpus": P.vm_job_cpus(v),
            "memory_gb": int(host.get("memory_gb", 6 * v + 6)),
            "minutes": cap + P.VM_JOB_EXTRA_MIN,
        },
        **extra,
    }
    if fill is not None:
        manifest["fill"] = fill
    return manifest


def prior_jobs(job: str, run_dirs: Sequence[Path]) -> list[dict[str, Any]]:
    """Every A1 job before ``job`` in the registered order, from their lane run directories
    (``manifest.json``, ``episodes.jsonl``, ``lane-receipt.json``), with digests."""
    found: dict[str, Path] = {}
    for run_dir in run_dirs:
        m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        a1 = m.get("a1") or {}
        name = P.a1_job(str(a1.get("size")), str(a1.get("session")))
        if m.get("purpose") != "a1" or name in found:
            raise ValueError(f"{run_dir} is not one distinct A1 job's run directory")
        found[name] = run_dir
    order = P.a1_job_order()
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


def gpu_for_vm_manifest(
    template: str, vm: Mapping[str, Any], *, vm_job_id: str, values: Mapping[str, str]
) -> str:
    """The GPU half of a registered pair, from its validated VM manifest: A0a runs 9B for
    A0a's 25 minutes; an A1 job runs its own size for the frozen T_A1."""
    purpose = vm.get("purpose")
    if purpose == "a0a":
        size = P.A0A_SIZE
    elif purpose == "a1":
        size = (vm.get("a1") or {}).get("size")
    else:
        raise ValueError("the GPU half belongs to a registered A0a or A1 VM job")
    minutes = int(vm["engine"]["gpu_cap_min"])
    return gpu_manifest(template, size=str(size), minutes=minutes, vm_job_id=vm_job_id,
                        values=values)  # fmt: skip


def gpu_manifest(
    template: str, *, size: str, minutes: int, vm_job_id: str, values: Mapping[str, str]
) -> str:
    """The GPU half of a pair: the template with every ``FILL_*`` slot filled.

    ``values`` holds the host-specific slots (``FILL_JOB``, ``FILL_OVERLAY_IMAGE_ID``,
    ``FILL_GIT_SHA``, ``FILL_SOURCE_SHA256``, ``FILL_RECEIPT_SHA256``,
    ``FILL_ARTIFACT_ROOT_SHA256``); the size, model, revision, cap and budget come from here.
    """
    if size not in MODELS:
        raise ValueError(f"size must be one of {sorted(MODELS)}")
    unknown = sorted(set(values) - set(HOST_FILLS))
    if unknown:
        raise ValueError(f"--values may hold only {list(HOST_FILLS)}, not {unknown}")
    if not re.fullmatch(r"[1-9][0-9]{0,19}", str(vm_job_id)):
        raise ValueError("the VM job id must be a Slurm job id")
    model_id, revision = MODELS[size]
    fills = {
        **{k: str(v) for k, v in values.items()},
        "FILL_SIZE": size,
        "FILL_MODEL_ID": model_id,
        "FILL_REVISION": revision,
        "FILL_VM_JOB_ID": str(vm_job_id),
        "FILL_CAP_MINUTES": str(int(minutes)),
        # The budget may never fall below the allocation (the submitter refuses that).
        "FILL_CAP_HOURS": f"{math.ceil(int(minutes) / 60 * 1e4) / 1e4:.4f}",
    }
    text = template
    for key in sorted(fills, key=len, reverse=True):
        text = text.replace(key, fills[key])
    left = sorted(set(re.findall(r"FILL_[A-Z0-9_]+", text)))
    if left:
        raise ValueError(f"unfilled template slots: {left}")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    vm = sub.add_parser("vm", help="a registered VM job's lane manifest")
    vm.add_argument("--purpose", choices=("a0a", "a1"), required=True)
    vm.add_argument("--host", type=Path, required=True)
    vm.add_argument("--source-dir", type=Path, default=PROJECT_ROOT)
    vm.add_argument("--n-star", type=int)
    vm.add_argument("--plan", help="the frozen plan file, relative to the source tree")
    vm.add_argument("--size", choices=P.SIZES)
    vm.add_argument("--session", choices=("S1", "S2"))
    vm.add_argument("--prior-run-dirs", type=Path, nargs="*", default=[])
    vm.add_argument("--out", type=Path, required=True)
    gpu = sub.add_parser("gpu", help="the GPU half of a registered pair, from its VM manifest")
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
        vm_m = lane.validate_manifest(
            json.loads(args.vm_manifest.read_text(encoding="utf-8")), args.source_dir
        )
        text = gpu_for_vm_manifest(template, vm_m, vm_job_id=args.vm_job_id, values=values)
        args.out.write_text(text, encoding="utf-8")
        print(hashlib.sha256(text.encode()).hexdigest())
        return 0
    manifest = vm_manifest(
        purpose=args.purpose,
        host=json.loads(args.host.read_text(encoding="utf-8")),
        source_dir=args.source_dir,
        n_star=args.n_star,
        plan_path=args.plan,
        size=args.size,
        session=args.session,
        prior_run_dirs=args.prior_run_dirs,
    )
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(hashlib.sha256(text.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
