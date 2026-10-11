#!/usr/bin/env python3
"""Host tool of r04-checker-nuisance-invariance-v1: image builds and CPU-only run plans.

Runs on the H100 host with its system Python 3.10 (standard library only) from a staged,
read-only export of the repository (``<root>/src/<sha>`` with ``.git_sha``). Every Slurm job
goes through the existing CPU lane ``infra/slurm/host-single-node/q2-mutation-cpu.sbatch``
of that export, unchanged (no GRES; the lane refuses a GPU, runs containers with
``--network=none``, a read-only root, no capabilities and the caller's uid:gid, and builds
images with ``--network=host``). Its receipts land in the checker-mutation study's receipt
directory as usual; run receipts are also copied into each run directory.

One job at a time: ``build`` and ``next`` submit only when ``squeue`` is empty (anyone's
job), and ``next`` submits a plan's next step only after the previous one finished with
exit status 0.

    r04_host.py build --src SRC --build B3
    r04_host.py check-image --build B3 --job JOB
    r04_host.py plan --src SRC --name dev-smoke-v1 --split dev --golds --s1a 1037 \
        --cells B0.ctrl_s.L0 ... --workers 8
    r04_host.py next --name dev-smoke-v1        # repeat until "complete"
    r04_host.py confirm --src SRC --name dev-smoke-v1 --round 1 --only IDS --cells ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

STAGE0 = Path("/home/kevin/cotcodec-runs/stage0")
ROOT = STAGE0 / "r04-nuisance"
Q2M = STAGE0 / "q2-evaluator-mutation"
S1A_RUNS = STAGE0 / "q2-stage1" / "runs"
INPUTS = Q2M / "inputs"
LANE = "infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
PY = "/opt/venv-lock/bin/python"


def load_levels(src: Path) -> Any:
    sys.path.insert(0, str(src))
    from harness.r04_nuisance import guard, levels

    return levels, guard


def check_src(src: Path) -> str:
    marker = src / ".git_sha"
    if not marker.is_file():
        raise SystemExit(f"{src} is not a staged export (no .git_sha)")
    return marker.read_text(encoding="utf-8").strip()


def queue_jobs() -> list[str]:
    out = subprocess.run(
        ["squeue", "-h", "-o", "%i %j %u %T"], capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def require_empty_queue() -> None:
    jobs = queue_jobs()
    if jobs:
        raise SystemExit("queue busy, not submitting: " + "; ".join(jobs))


def hexargv(argv: list[str]) -> str:
    return json.dumps(argv).encode().hex()


def image_id(ref: str) -> str:
    out = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", ref],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def image_layers(ref: str) -> list[str]:
    out = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", ref],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def sbatch(command: list[str]) -> str:
    out = subprocess.run(command, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"sbatch failed: {out.stderr.strip()}")
    return out.stdout.strip().split(";")[0]


# --- images -----------------------------------------------------------------------------


def cmd_build(args: argparse.Namespace) -> None:
    sha = check_src(args.src)
    levels, _ = load_levels(args.src)
    build = levels.BUILD_BY_ID[args.build]
    if build.source != "tdf":
        raise SystemExit(f"{args.build} is not a derived build")
    if image_id(levels.LO_VM_TAG) != levels.LO_VM_IMAGE_ID:
        raise SystemExit(f"{levels.LO_VM_TAG} does not name {levels.LO_VM_IMAGE_ID}")
    dockerfile = args.src / "infra" / "r04-nuisance" / "lo-tdf" / build.id / "Dockerfile"
    digest = hashlib.sha256(dockerfile.read_bytes()).hexdigest()
    context = ROOT / "images" / f"{build.id}-{digest[:12]}"
    context.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dockerfile, context / "Dockerfile")
    tag = f"cotcodec-q2-r04-lo-{build.id.lower()}:{digest[:12]}"
    require_empty_queue()
    command = [
        "sbatch",
        "--parsable",
        f"--job-name=r04-build-{build.id}",
        "--cpus-per-task=8",
        "--mem=16G",
        "--time=00:45:00",
        f"--output={ROOT}/slurm/slurm-%x-%j.out",
        f"--export=ALL,Q2M_MODE=build,Q2M_CONTEXT={context},Q2M_TAG={tag}",
        str(args.src / LANE),
    ]
    job = sbatch(command)
    record = {
        "build": build.id,
        "job": job,
        "tag": tag,
        "dockerfile_sha256": digest,
        "context": str(context),
        "src_sha": sha,
        "command": command,
        "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (ROOT / "images" / f"{build.id}-submit-{job}.json").write_text(json.dumps(record, indent=1))
    print(json.dumps(record))


def cmd_check_image(args: argparse.Namespace) -> None:
    levels, _ = load_levels(args.src)
    receipt_path = Q2M / "receipts" / f"build-{args.job}.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    derived = receipt["image_id"]
    base_layers = image_layers(levels.LO_VM_IMAGE_ID)
    layers = image_layers(derived)
    if layers[: len(base_layers)] != base_layers or len(layers) <= len(base_layers):
        raise SystemExit(f"{derived} does not extend the LO-VM image's layers")
    record = {
        "build": args.build,
        "image_id": derived,
        "tag": receipt["tag"],
        "build_receipt": receipt,
        "base_image_id": levels.LO_VM_IMAGE_ID,
        "base_layers": len(base_layers),
        "layers": len(layers),
        "added_layers": layers[len(base_layers) :],
    }
    shutil.copyfile(receipt_path, ROOT / "images" / f"build-{args.job}.json")
    log = Q2M / "receipts" / f"build-{args.job}.log"
    if log.is_file():
        shutil.copyfile(log, ROOT / "images" / f"build-{args.job}.log")
    (ROOT / "images" / f"{args.build}.json").write_text(json.dumps(record, indent=1))
    images_path = ROOT / "images" / "images.json"
    images = json.loads(images_path.read_text()) if images_path.is_file() else {}
    images["B0"] = levels.LO_VM_IMAGE_ID
    images[args.build] = derived
    images_path.write_text(json.dumps(dict(sorted(images.items())), indent=1))
    print(json.dumps({k: v for k, v in record.items() if k != "build_receipt"}))


# --- run plans --------------------------------------------------------------------------


def lane_run(
    name: str,
    image: str,
    argv: list[str],
    src: Path,
    run_dir: Path,
    *,
    extra_ro: list[str],
    cpus: int,
    minutes: int,
) -> dict[str, Any]:
    env = [
        "ALL",
        "Q2M_MODE=run",
        f"Q2M_IMAGE_ID={image}",
        f"Q2M_ARGV_JSON_HEX={hexargv(argv)}",
        f"Q2M_SOURCE={src}",
        f"Q2M_RUN_DIR={run_dir}",
        f"Q2M_INPUTS={INPUTS}",
        "Q2M_TMPFS_SIZE=32g",
    ]
    if extra_ro:
        env.append("Q2M_EXTRA_RO=" + "+".join(extra_ro))
    command = [
        "sbatch",
        "--parsable",
        f"--job-name=r04-{name}",
        f"--cpus-per-task={cpus}",
        "--mem=96G",
        f"--time={minutes // 60:02d}:{minutes % 60:02d}:00",
        f"--output={ROOT}/slurm/slurm-%x-%j.out",
        "--export=" + ",".join(env),
        str(src / LANE),
    ]
    return {
        "name": name,
        "image": image,
        "argv": argv,
        "run_dir": str(run_dir),
        "command": command,
        "job": None,
        "state": "pending",
    }


def s1a_mounts(labels: list[str]) -> list[str]:
    out = []
    for label in labels:
        path = S1A_RUNS / label
        if not (path / "episodes.jsonl").is_file():
            raise SystemExit(f"no S1a run {path}")
        out.append(f"{path}:/ro/s1a-{label}")
    return out


def save_steps(
    src: Path,
    run: Path,
    out_name: str,
    cells: list[str],
    images: dict[str, str],
    levels: Any,
    *,
    s1a_ro: list[str],
    workers: int,
    only: str | None,
    minutes: int,
) -> list[dict[str, Any]]:
    steps = []
    by_build: dict[str, list[str]] = {}
    for cid in cells:
        by_build.setdefault(levels.get_cell(cid).build, []).append(cid)
    extra = [f"{run / 'items'}:/ro/items", *s1a_ro]
    only_arg = "-"
    if only:
        extra.append(f"{Path(only).parent}:/ro/only")
        only_arg = f"/ro/only/{Path(only).name}"
    for build in sorted(by_build):
        if build not in images:
            raise SystemExit(f"no image for build {build}; run check-image first")
        argv = [
            "sh",
            "/src/infra/r04-nuisance/run/resave.sh",
            "/ro/items/items.jsonl",
            "/out",
            str(workers),
            only_arg,
            *by_build[build],
        ]
        steps.append(
            lane_run(
                f"{out_name}-save-{build}",
                images[build],
                argv,
                src,
                run / out_name / "saves",
                extra_ro=extra,
                cpus=min(32, 2 * workers),
                minutes=minutes,
            )
        )
    return steps


def score_step(
    src: Path,
    run: Path,
    out_name: str,
    cells: list[str],
    levels: Any,
    *,
    s1a_ro: list[str],
    workers: int,
    only: str | None,
    raw: bool,
    minutes: int,
) -> dict[str, Any]:
    argv = [
        PY,
        "-m",
        "harness.r04_nuisance.score",
        "--items",
        "/ro/items/items.jsonl",
        "--saves-root",
        "/ro/saves",
        "--saves-prefix",
        "/out",
        "--osworld",
        "/inputs/OSWorld",
        "--file-cache",
        "/inputs/file_cache_1e112283/files",
        "--vm-baseline",
        "/inputs/vm-baseline",
        "--out",
        "/out",
        "--workers",
        str(workers),
    ]
    if raw:
        argv += ["--cell", "raw"]
    for cid in cells:
        argv += ["--cell", f"{cid}=/ro/saves/{cid}"]
    extra = [f"{run / 'items'}:/ro/items", f"{run / out_name / 'saves'}:/ro/saves", *s1a_ro]
    if only:
        extra.append(f"{Path(only).parent}:/ro/only")
        argv += ["--only", f"/ro/only/{Path(only).name}"]
    return lane_run(
        f"{out_name}-score",
        levels.METRIC_IMAGE_ID,
        argv,
        src,
        run / out_name / "scores",
        extra_ro=extra,
        cpus=min(32, 2 * workers),
        minutes=minutes,
    )


def load_images(levels: Any) -> dict[str, str]:
    path = ROOT / "images" / "images.json"
    images = json.loads(path.read_text()) if path.is_file() else {}
    images["B0"] = levels.LO_VM_IMAGE_ID
    return images


def cmd_plan(args: argparse.Namespace) -> None:
    sha = check_src(args.src)
    levels, guard = load_levels(args.src)
    images = load_images(levels)
    used = {b: images.get(b) for b in {levels.get_cell(c).build for c in args.cells}}
    guard.require_split_allowed(args.split, args.src, {b: i for b, i in used.items() if i})
    run = ROOT / "runs" / args.name
    if run.exists():
        raise SystemExit(f"{run} exists; version the run name")
    (run / "items").mkdir(parents=True)
    s1a_ro = s1a_mounts(args.s1a)
    items_argv = [
        PY,
        "-m",
        "harness.r04_nuisance.items",
        "--splits",
        "/src/program/evidence/q2-mutation/splits.json",
        "--split",
        args.split,
        "--out",
        "/out/items.jsonl",
    ]
    if args.golds:
        items_argv += [
            "--golds",
            "--osworld",
            "/inputs/OSWorld",
            "--file-cache",
            "/inputs/file_cache_1e112283/files",
        ]
    for label in args.s1a:
        items_argv += ["--s1a-run", f"{label}=/ro/s1a-{label}"]
    env_prefix = ["env", f"R04_PREREG_FROZEN={levels.EXPERIMENT_ID}"] if args.split != "dev" else []
    steps = [
        lane_run(
            "items",
            levels.METRIC_IMAGE_ID,
            env_prefix + items_argv,
            args.src,
            run / "items",
            extra_ro=s1a_ro,
            cpus=4,
            minutes=30,
        )
    ]
    steps += save_steps(
        args.src,
        run,
        "main",
        args.cells,
        images,
        levels,
        s1a_ro=s1a_ro,
        workers=args.workers,
        only=None,
        minutes=args.save_minutes,
    )
    steps.append(
        score_step(
            args.src,
            run,
            "main",
            args.cells,
            levels,
            s1a_ro=s1a_ro,
            workers=args.workers,
            only=None,
            raw=True,
            minutes=args.score_minutes,
        )
    )
    plan = {
        "name": args.name,
        "split": args.split,
        "src": str(args.src),
        "src_sha": sha,
        "cells": args.cells,
        "s1a": args.s1a,
        "golds": args.golds,
        "images": used,
        "steps": steps,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (run / "plan.json").write_text(json.dumps(plan, indent=1))
    print(json.dumps({"plan": str(run / "plan.json"), "steps": [s["name"] for s in steps]}))


def cmd_confirm(args: argparse.Namespace) -> None:
    check_src(args.src)
    levels, _ = load_levels(args.src)
    run = ROOT / "runs" / args.name
    plan = json.loads((run / "plan.json").read_text())
    if args.src != Path(plan["src"]):
        raise SystemExit("confirmation rounds run from the plan's own staged export")
    cells = list(dict.fromkeys([levels.CONTROL_CELL, *args.cells]))
    only = run / f"round-{args.round}" / "only.txt"
    only.parent.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.only, only)
    images = load_images(levels)
    s1a_ro = s1a_mounts(plan["s1a"])
    out = f"round-{args.round}"
    steps = save_steps(
        args.src,
        run,
        out,
        cells,
        images,
        levels,
        s1a_ro=s1a_ro,
        workers=args.workers,
        only=str(only),
        minutes=args.save_minutes,
    )
    steps.append(
        score_step(
            args.src,
            run,
            out,
            cells,
            levels,
            s1a_ro=s1a_ro,
            workers=args.workers,
            only=str(only),
            raw=False,
            minutes=args.score_minutes,
        )
    )
    plan["steps"] += steps
    (run / "plan.json").write_text(json.dumps(plan, indent=1))
    print(json.dumps({"added": [s["name"] for s in steps]}))


def step_finished(step: dict[str, Any]) -> str | None:
    """done, failed, or None while the job is queued or running."""
    job = step["job"]
    if any(line.split()[0] == job for line in queue_jobs()):
        return None
    receipt = Path(step["run_dir"]) / f"receipt-{job}.json"
    if receipt.is_file():
        status = json.loads(receipt.read_text())["exit_status"]
        return "done" if status == 0 else "failed"
    return "failed"


def cmd_next(args: argparse.Namespace) -> None:
    run = ROOT / "runs" / args.name
    plan_path = run / "plan.json"
    plan = json.loads(plan_path.read_text())
    for step in plan["steps"]:
        if step["state"] == "done":
            continue
        if step["state"] == "failed":
            print(json.dumps({"state": "failed", "step": step["name"], "job": step["job"]}))
            return
        if step["state"] == "submitted":
            result = step_finished(step)
            if result is None:
                print(json.dumps({"state": "running", "step": step["name"], "job": step["job"]}))
                return
            step["state"] = result
            step["finished_seen_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            plan_path.write_text(json.dumps(plan, indent=1))
            if result == "failed":
                print(json.dumps({"state": "failed", "step": step["name"], "job": step["job"]}))
                return
            continue
        jobs = queue_jobs()
        if jobs:
            print(json.dumps({"state": "waiting_for_queue", "step": step["name"], "queue": jobs}))
            return
        Path(step["run_dir"]).mkdir(parents=True, exist_ok=True)
        step["job"] = sbatch(step["command"])
        step["state"] = "submitted"
        step["submitted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        plan_path.write_text(json.dumps(plan, indent=1))
        print(json.dumps({"state": "submitted", "step": step["name"], "job": step["job"]}))
        return
    print(json.dumps({"state": "complete", "name": args.name}))


def main(argv: list[str] | None = None) -> int:
    os.umask(0o022)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--src", type=Path, required=True)
    b.add_argument("--build", required=True)
    c = sub.add_parser("check-image")
    c.add_argument("--src", type=Path, required=True)
    c.add_argument("--build", required=True)
    c.add_argument("--job", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--src", type=Path, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--split", required=True, choices=["dev", "confirm", "reserve"])
    p.add_argument("--golds", action="store_true")
    p.add_argument("--s1a", nargs="*", default=[], help="S1a lane run ids (directory names)")
    p.add_argument("--cells", nargs="+", required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--save-minutes", type=int, default=60)
    p.add_argument("--score-minutes", type=int, default=90)
    f = sub.add_parser("confirm")
    f.add_argument("--src", type=Path, required=True)
    f.add_argument("--name", required=True)
    f.add_argument("--round", type=int, required=True)
    f.add_argument("--only", type=Path, required=True)
    f.add_argument("--cells", nargs="+", required=True)
    f.add_argument("--workers", type=int, default=8)
    f.add_argument("--save-minutes", type=int, default=60)
    f.add_argument("--score-minutes", type=int, default=90)
    n = sub.add_parser("next")
    n.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    {
        "build": cmd_build,
        "check-image": cmd_check_image,
        "plan": cmd_plan,
        "confirm": cmd_confirm,
        "next": cmd_next,
    }[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
