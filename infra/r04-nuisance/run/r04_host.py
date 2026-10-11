#!/usr/bin/env python3
"""Host tool of r04-checker-nuisance-invariance-v1: image builds and CPU-only run plans.

Runs on the H100 host with its system Python 3.10 (standard library only) from a staged,
read-only export of the repository (``<root>/src/<sha>`` with ``.git_sha``). Every Slurm job
goes through the existing CPU lane ``infra/slurm/host-single-node/q2-mutation-cpu.sbatch``
of that export, unchanged (no GRES; the lane refuses a GPU, runs containers with
``--network=none``, a read-only root, no capabilities and the caller's uid:gid, and builds
images with ``--network=host``). Its receipts land in the checker-mutation study's receipt
directory as usual and in each step's own directory.

One job at a time: ``build`` and ``next`` submit only when ``squeue`` is empty (anyone's
job), and ``next`` submits a plan's next step only after the previous one finished.

A plan is a list of steps (items; one save job per build, the replicate in its own; the
score jobs of ``levels.score_groups``, secondary last; later both confirmation rounds), each
with its own output directory. ``next`` renders a step's job when it submits it: the time
limit is ``levels.limit_minutes`` of the step's projection from its item count, and a score
job reads the save directory of the attempt that finished. A job that fails (exit status
other than 0, or no receipt) is rerun in full as a new attempt with a fresh directory
(``<dir>.a2``, ``.a3``), at most twice; a third failure ends the step (``failed_final``).
Under a cap (the registered run's 20 lane-hours, main run and rounds together), no job is
submitted once the lane hours used reach the cap (the rest are ``not_run``), and before a
secondary score job is submitted, if the hours used plus the projection of every step left
exceed the cap, the secondary score jobs are dropped (``dropped``).

    r04_host.py build --src SRC --build B3
    r04_host.py check-image --src SRC --build B3 --job JOB
    r04_host.py plan --src SRC --name r04-v1 --registered       # R04_PREREG_FROZEN exported
    r04_host.py plan --src SRC --name dev-smoke-v5 --split dev --golds --s1a 1037 \\
        --cells B0.ctrl_s.L0 ... --workers 8
    r04_host.py next --name NAME                 # repeat until "complete"
    r04_host.py confirm --name NAME --pending PENDING.json   # both rounds, then next again
    r04_host.py status --name NAME
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

STAGE0 = Path("/home/kevin/cotcodec-runs/stage0")
ROOT = STAGE0 / "r04-nuisance"
Q2M = STAGE0 / "q2-evaluator-mutation"
S1A_RUNS = STAGE0 / "q2-stage1" / "runs"
INPUTS = Q2M / "inputs"
LANE = "infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
PY = "/opt/venv-lock/bin/python"
MAX_ATTEMPTS = 3  # a failed job is rerun at most twice
ITEMS_MINUTES = 60
TERMINAL = ("done", "superseded", "failed_final", "not_run", "dropped")


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


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
        "submitted_at": now(),
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


# --- plan steps ---------------------------------------------------------------------------


def s1a_mounts(labels: list[str]) -> list[str]:
    out = []
    for label in labels:
        path = S1A_RUNS / label
        if not (path / "episodes.jsonl").is_file():
            raise SystemExit(f"no S1a run {path}")
        out.append(f"{path}:/ro/s1a-{label}")
    return out


def lane_command(
    name: str, image: str, argv: list[str], src: Path, run_dir: Path, extra_ro: list[str],
    cpus: int, minutes: int,
) -> list[str]:  # fmt: skip
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
    return [
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


def step_spec(
    name: str, kind: str, out: str, group: str, role: str, cells: list[str], run_dir: Path,
    image: str,
) -> dict[str, Any]:  # fmt: skip
    return {
        "name": name,
        "kind": kind,
        "out": out,
        "group": group,
        "role": role,
        "cells": cells,
        "attempt": 1,
        "run_dir": str(run_dir),
        "image": image,
        "state": "pending",
        "job": None,
        "command": None,
    }


def save_specs(
    run: Path, out: str, cells: list[str], images: dict[str, str], levels: Any
) -> list[dict[str, Any]]:
    """One save job per build, the replicate in its own (``levels.save_groups``)."""
    steps = []
    for group, members in levels.save_groups(cells):
        build = group.split(".")[0]
        if build not in images:
            raise SystemExit(f"no image for build {build}; run check-image first")
        role = "control" if levels.CONTROL_CELL in members or group.endswith(".r2") else "save"
        steps.append(
            step_spec(
                f"{out}-save-{group}",
                "save",
                out,
                group,
                role,
                members,
                run / out / "saves" / group,
                images[build],
            )  # fmt: skip
        )
    return steps


def score_specs(
    run: Path, out: str, cells: list[str], levels: Any, *, raw: bool
) -> list[dict[str, Any]]:
    """The main run's score jobs (``levels.score_groups``), or one job for a round."""
    if out != "main":
        return [
            step_spec(
                f"{out}-score",
                "score",
                out,
                "round",
                "round",
                list(cells),
                run / out / "scores" / "round",
                levels.METRIC_IMAGE_ID,
            )  # fmt: skip
        ]
    return [
        step_spec(
            f"{out}-score-{group}",
            "score",
            out,
            group,
            role,
            members,
            run / out / "scores" / group,
            levels.METRIC_IMAGE_ID,
        )  # fmt: skip
        for group, role, members in levels.score_groups(cells, raw)
    ]


def count_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def step_items(plan: dict[str, Any], step: dict[str, Any]) -> int:
    run = Path(plan["run_root"])
    if step["out"] != "main":
        return count_lines(run / "rounds" / "only.txt")
    items = run / "items" / "items.jsonl"
    return count_lines(items) if items.is_file() else 0


def projected(plan: dict[str, Any], step: dict[str, Any], levels: Any) -> float:
    if step["kind"] == "items":
        return 0.0
    rate = (
        levels.SAVE_SECONDS_PER_ITEM_CELL
        if step["kind"] == "save"
        else levels.SCORE_SECONDS_PER_ITEM_CELL
    )
    n = step_items(plan, step) or levels.REGISTERED_ITEMS
    return levels.projected_minutes(n, len(step["cells"]), plan["workers"], rate)


def render(plan: dict[str, Any], step: dict[str, Any], levels: Any) -> list[str] | None:
    """The step's sbatch command, or None if it has nothing left to run (a score job whose
    cells' save jobs all ended without saving; ``not_scored`` names them)."""
    src = Path(plan["src"])
    run = Path(plan["run_root"])
    s1a_ro = s1a_mounts(plan["s1a"])
    workers = int(plan["workers"])
    run_dir = Path(step["run_dir"])
    if step["kind"] == "items":
        argv = [
            PY, "-m", "harness.r04_nuisance.items",
            "--splits", "/src/program/evidence/q2-mutation/splits.json",
            "--split", *plan["splits"],
            "--out", "/out/items.jsonl", "--inputs", "/inputs",
        ]  # fmt: skip
        if plan["golds"]:
            argv += ["--golds", "--osworld", "/inputs/OSWorld",
                     "--file-cache", "/inputs/file_cache_1e112283/files"]  # fmt: skip
        for label in plan["s1a"]:
            argv += ["--s1a-run", f"{label}=/ro/s1a-{label}"]
        if plan["splits"] != ["dev"]:
            argv = ["env", f"R04_PREREG_FROZEN={levels.EXPERIMENT_ID}", *argv]
        step["minutes"] = ITEMS_MINUTES
        return lane_command(
            step["name"], step["image"], argv, src, run_dir, s1a_ro, 4, ITEMS_MINUTES
        )
    extra = [f"{run / 'items'}:/ro/items", *s1a_ro]
    only_arg = "-"
    if step["out"] != "main":
        extra.append(f"{run / 'rounds'}:/ro/only")
        only_arg = "/ro/only/only.txt"
    cpus = min(32, 2 * workers)
    if step["kind"] == "save":
        step["projected_minutes"] = round(projected(plan, step, levels), 1)
        step["minutes"] = levels.limit_minutes(step["projected_minutes"])
        argv = ["sh", "/src/infra/r04-nuisance/run/resave.sh", "/ro/items/items.jsonl", "/out",
                str(workers), only_arg, *step["cells"]]  # fmt: skip
        return lane_command(
            step["name"], step["image"], argv, src, run_dir, extra, cpus, step["minutes"]
        )
    argv = [
        PY, "-m", "harness.r04_nuisance.score", "--items", "/ro/items/items.jsonl",
        "--saves-prefix", "/out", "--osworld", "/inputs/OSWorld",
        "--file-cache", "/inputs/file_cache_1e112283/files", "--vm-baseline", "/inputs/vm-baseline",
        "--out", "/out", "--workers", str(workers),
    ]  # fmt: skip
    saves = {}
    for other in plan["steps"]:
        if other["kind"] == "save" and other["out"] == step["out"] and other["state"] == "done":
            for cid in other["cells"]:
                saves[cid] = Path(other["run_dir"]).name
    not_scored = {}
    chosen = []
    for cid in step["cells"]:
        if cid == levels.RAW:
            argv += ["--cell", "raw"]
            chosen.append(cid)
        elif cid in saves:
            argv += ["--cell", f"{cid}=/ro/saves/{saves[cid]}/{cid}"]
            chosen.append(cid)
        else:
            not_scored[cid] = "its save job ended without a finished attempt"
    step["not_scored"] = not_scored
    if not chosen:
        return None
    if only_arg != "-":
        argv += ["--only", only_arg]
    extra.append(f"{run / step['out'] / 'saves'}:/ro/saves")
    step["projected_minutes"] = round(
        levels.projected_minutes(
            step_items(plan, step), len(chosen), workers, levels.SCORE_SECONDS_PER_ITEM_CELL
        ),
        1,
    )
    step["minutes"] = levels.limit_minutes(step["projected_minutes"])
    return lane_command(
        step["name"], step["image"], argv, src, run_dir, extra, cpus, step["minutes"]
    )


def load_images(levels: Any) -> dict[str, str]:
    path = ROOT / "images" / "images.json"
    images = json.loads(path.read_text()) if path.is_file() else {}
    images["B0"] = levels.LO_VM_IMAGE_ID
    return images


def cmd_plan(args: argparse.Namespace) -> None:
    sha = check_src(args.src)
    levels, guard = load_levels(args.src)
    if args.registered:
        if args.split or args.golds or args.s1a or args.cells or args.workers:
            raise SystemExit("--registered fixes the splits, items, cells and workers")
        reg = levels.REGISTERED_RUN
        splits, golds, s1a = list(reg["splits"]), bool(reg["golds"]), list(reg["s1a_runs"])
        cells, workers, cap = list(reg["cells"]), int(reg["workers"]), reg["cap_lane_hours"]
    else:
        if not (args.split and args.cells):
            raise SystemExit("give --registered, or --split and --cells (smoke tests)")
        splits, golds, s1a = list(args.split), args.golds, list(args.s1a)
        cells, workers, cap = list(args.cells), args.workers or 8, args.cap_lane_hours
        if list(levels.check_split_set(splits)) != ["dev"]:
            raise SystemExit("the registered splits run only as --registered")
    splits = list(levels.check_split_set(splits))
    for cid in cells:
        levels.get_cell(cid)
    if levels.CONTROL_CELL not in cells:
        raise SystemExit("every plan holds the control cell")
    images = load_images(levels)
    used = {b: images.get(b) for b in {levels.get_cell(c).build for c in cells}}
    guard.require_splits_allowed(splits, args.src, {b: i for b, i in used.items() if i})
    run = ROOT / "runs" / args.name
    if run.exists():
        raise SystemExit(f"{run} exists; version the run name")
    s1a_mounts(s1a)
    steps = [
        step_spec(
            "items", "items", "main", "items", "items", [], run / "items", levels.METRIC_IMAGE_ID
        )  # fmt: skip
    ]
    steps += save_specs(run, "main", cells, images, levels)
    steps += score_specs(run, "main", cells, levels, raw=True)
    run.mkdir(parents=True)
    plan = {
        "name": args.name,
        "registered": bool(args.registered),
        "splits": splits,
        "src": str(args.src),
        "src_sha": sha,
        "run_root": str(run),
        "cells": cells,
        "s1a": s1a,
        "golds": golds,
        "workers": workers,
        "cap_lane_hours": cap,
        "images": used,
        "steps": steps,
        "rounds": None,
        "created_at": now(),
    }
    write_plan(run, plan)
    print(json.dumps({"plan": str(run / "plan.json"), "steps": [s["name"] for s in steps]}))


def write_plan(run: Path, plan: dict[str, Any]) -> None:
    tmp = run / "plan.json.tmp"
    tmp.write_text(json.dumps(plan, indent=1))
    tmp.replace(run / "plan.json")


def read_plan(name: str) -> tuple[Path, dict[str, Any]]:
    run = ROOT / "runs" / name
    return run, json.loads((run / "plan.json").read_text())


def cmd_confirm(args: argparse.Namespace) -> None:
    """Add both confirmation rounds: the control and every cell with a pending discordance,
    on the pending items only (the registered analysis's ``--pending-out`` of this run)."""
    run, plan = read_plan(args.name)
    levels, _ = load_levels(Path(plan["src"]))
    if plan.get("rounds"):
        raise SystemExit("this run's confirmation rounds exist already")
    open_steps = [s["name"] for s in plan["steps"] if s["state"] not in TERMINAL]
    if open_steps:
        raise SystemExit(f"the main run is not finished: {open_steps}")
    pending = json.loads(args.pending.read_text(encoding="utf-8"))
    items, cells = sorted(pending["items"]), sorted(pending["cells"])
    if not items or not cells:
        raise SystemExit("nothing is pending; no confirmation round runs")
    for cid in cells:
        levels.get_cell(cid)
    (run / "rounds").mkdir(exist_ok=False)
    (run / "rounds" / "pending.json").write_text(
        json.dumps({"items": items, "cells": cells}, indent=1, sort_keys=True)
    )
    (run / "rounds" / "only.txt").write_text("".join(f"{i}\n" for i in items))
    round_cells = list(dict.fromkeys([levels.CONTROL_CELL, *cells]))
    images = load_images(levels)
    added = []
    for out in ("round-1", "round-2"):
        steps = save_specs(run, out, round_cells, images, levels)
        steps += score_specs(run, out, round_cells, levels, raw=False)
        plan["steps"] += steps
        added += [s["name"] for s in steps]
    plan["rounds"] = {"pending": {"items": items, "cells": cells}, "added_at": now()}
    write_plan(run, plan)
    print(json.dumps({"added": added}))


def receipt_of(step: dict[str, Any]) -> dict[str, Any] | None:
    path = Path(step["run_dir"]) / f"receipt-{step['job']}.json"
    return json.loads(path.read_text()) if path.is_file() else None


def step_finished(step: dict[str, Any]) -> str | None:
    """done, failed, or None while the job is queued or running."""
    job = step["job"]
    if any(line.split()[0] == job for line in queue_jobs()):
        return None
    receipt = receipt_of(step)
    if receipt is not None:
        return "done" if receipt["exit_status"] == 0 else "failed"
    return "failed"


def _seconds(start: str, end: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).total_seconds()


def step_hours(step: dict[str, Any]) -> float:
    """Lane wall-clock hours of a finished job: its receipt's start to finish, or (no
    receipt) the time from submission to when its end was seen."""
    if not step.get("job") or step["state"] in ("pending", "submitted"):
        return 0.0
    receipt = receipt_of(step)
    if receipt is not None:
        return _seconds(receipt["started_at"], receipt["finished_at"]) / 3600.0
    if step.get("submitted_at") and step.get("finished_seen_at"):
        return _seconds(step["submitted_at"], step["finished_seen_at"]) / 3600.0
    return 0.0


def hours_used(plan: dict[str, Any]) -> float:
    return sum(step_hours(s) for s in plan["steps"])


def projected_remaining(plan: dict[str, Any], levels: Any) -> float:
    """Hours the steps left would take: their projections, scaled by how the finished save
    and score jobs' hours compared with their projections."""
    done = [s for s in plan["steps"] if s["state"] == "done" and s.get("projected_minutes")]
    actual = sum(step_hours(s) for s in done)
    planned = sum(s["projected_minutes"] / 60.0 for s in done)
    scale = max(1.0, actual / planned) if planned > 0 else 1.0
    left = [s for s in plan["steps"] if s["state"] == "pending"]
    return scale * sum(projected(plan, s, levels) / 60.0 for s in left)


def handle_failure(plan: dict[str, Any], index: int) -> str:
    """A failed job: a new attempt in a fresh directory, or the end of the step."""
    step = plan["steps"][index]
    cap = plan.get("cap_lane_hours")
    if step["attempt"] >= MAX_ATTEMPTS:
        step["state"] = "failed_final"
        step["reason"] = f"failed {MAX_ATTEMPTS} times"
        return step["state"]
    if cap is not None and hours_used(plan) >= cap:
        step["state"] = "failed_final"
        step["reason"] = "failed; the lane-hour cap leaves no rerun"
        return step["state"]
    retry = copy.deepcopy(step)
    base_dir = step["run_dir"].rsplit(".a", 1)[0] if step["attempt"] > 1 else step["run_dir"]
    base_name = step["name"].rsplit(".a", 1)[0] if step["attempt"] > 1 else step["name"]
    retry["attempt"] = step["attempt"] + 1
    retry["run_dir"] = f"{base_dir}.a{retry['attempt']}"
    retry["name"] = f"{base_name}.a{retry['attempt']}"
    for key in ("job", "command", "submitted_at", "finished_seen_at", "reason", "not_scored"):
        retry[key] = None
    retry["state"] = "pending"
    step["state"] = "superseded"
    plan["steps"].insert(index + 1, retry)
    return "retry"


def cmd_next(args: argparse.Namespace) -> None:
    run, plan = read_plan(args.name)
    levels, _ = load_levels(Path(plan["src"]))
    cap = plan.get("cap_lane_hours")
    index = 0
    while index < len(plan["steps"]):
        step = plan["steps"][index]
        if step["state"] in TERMINAL:
            index += 1
            continue
        if step["state"] == "submitted":
            result = step_finished(step)
            if result is None:
                print(json.dumps({"state": "running", "step": step["name"], "job": step["job"]}))
                return
            step["state"] = result
            step["finished_seen_at"] = now()
        if step["state"] == "failed":
            outcome = handle_failure(plan, index)
            write_plan(run, plan)
            print(json.dumps({"failed": step["name"], "job": step["job"], "then": outcome}))
            index += 1
            continue
        if step["state"] == "done":
            write_plan(run, plan)
            index += 1
            continue
        # pending: the cap, then the queue, then submit
        used = hours_used(plan)
        if cap is not None and used >= cap:
            for other in plan["steps"]:
                if other["state"] == "pending":
                    other["state"] = "not_run"
                    other["reason"] = f"the lane-hour cap ({cap} h) was reached at {used:.2f} h"
            write_plan(run, plan)
            print(json.dumps({"state": "cap_reached", "hours_used": round(used, 2)}))
            return
        if cap is not None and step["role"] == "secondary":
            remaining = projected_remaining(plan, levels)
            if used + remaining > cap:
                for other in plan["steps"]:
                    if other["state"] == "pending" and other["role"] == "secondary":
                        other["state"] = "dropped"
                        other["reason"] = (
                            f"projected {used + remaining:.2f} h exceeds the {cap} h cap"
                        )
                write_plan(run, plan)
                continue
        jobs = queue_jobs()
        if jobs:
            print(json.dumps({"state": "waiting_for_queue", "step": step["name"], "queue": jobs}))
            return
        command = render(plan, step, levels)
        if command is None:
            step["state"] = "not_run"
            step["reason"] = "no cell left to score"
            write_plan(run, plan)
            continue
        Path(step["run_dir"]).mkdir(parents=True, exist_ok=False)
        step["command"] = command
        step["job"] = sbatch(command)
        step["state"] = "submitted"
        step["submitted_at"] = now()
        write_plan(run, plan)
        print(json.dumps({"state": "submitted", "step": step["name"], "job": step["job"]}))
        return
    write_plan(run, plan)
    print(json.dumps({"state": "complete", "name": args.name, "hours_used": hours_used(plan)}))


def cmd_status(args: argparse.Namespace) -> None:
    _run, plan = read_plan(args.name)
    levels, _ = load_levels(Path(plan["src"]))
    print(
        json.dumps(
            {
                "name": plan["name"],
                "hours_used": round(hours_used(plan), 3),
                "projected_remaining_hours": round(projected_remaining(plan, levels), 3),
                "cap_lane_hours": plan.get("cap_lane_hours"),
                "steps": [
                    {k: s.get(k) for k in ("name", "state", "job", "minutes", "reason")}
                    for s in plan["steps"]
                ],
            },
            indent=1,
        )
    )


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
    p.add_argument("--registered", action="store_true", help="the registered run (section 6)")
    p.add_argument("--split", nargs="+", choices=["dev", "confirm", "reserve"])
    p.add_argument("--golds", action="store_true")
    p.add_argument("--s1a", nargs="*", default=[], help="S1a lane run ids (directory names)")
    p.add_argument("--cells", nargs="+")
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--cap-lane-hours", type=float, default=None)
    f = sub.add_parser("confirm")
    f.add_argument("--name", required=True)
    f.add_argument("--pending", type=Path, required=True, help="the analysis's --pending-out")
    n = sub.add_parser("next")
    n.add_argument("--name", required=True)
    s = sub.add_parser("status")
    s.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    {
        "build": cmd_build,
        "check-image": cmd_check_image,
        "plan": cmd_plan,
        "confirm": cmd_confirm,
        "next": cmd_next,
        "status": cmd_status,
    }[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
