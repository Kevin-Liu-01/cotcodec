#!/usr/bin/env python3
"""Host tool of q2-zinv-reserve-validation-v1: plan and submit its four CPU-only steps.

Runs on the H100 host with its system Python 3.10 (standard library only) from a staged,
read-only export of the repository (``<ROOT>/src/<sha>`` with ``.git_sha``). Every step is one
Slurm job through the existing CPU lane ``infra/slurm/host-single-node/q2-mutation-cpu.sbatch``
of that export, unchanged (no GRES; the lane refuses a GPU and runs GPU-less, network-less
containers with a read-only root, no capabilities and the caller's uid:gid). Receipts land in
the checker-mutation study's receipt directory and in each step's own directory.

One job at a time: ``next`` submits only when ``squeue`` shows no job at all (anyone's), and a
step only after the previous step's receipt reports exit status 0. A failed step (exit status
other than 0, or no receipt) is rerun once in full in a fresh directory (``<dir>.a2``); a
second failure ends the plan (``failed_final``). No job is submitted once the lane hours used
(receipt start to finish) reach the cap.

The steps (registration section 5); the parent's three mutation jobs are the commands of its
frozen ``infra/q2-mutation/run/submit_mutants.sh``, submitted one at a time:

1. ``targets`` (metric image): this addendum's guard, the parent's job 1 (``campaign guard``,
   ``make_jobs.sh``, ``campaign targets``), then ``run select-targets`` (pptx only).
2. ``build`` (LO-VM image): the parent's job 2 (``campaign build --apply-to gold``, ``reach.sh``).
3. ``score`` (metric image): this addendum's guard, then the parent's job 3 (``campaign guard``,
   ``k2-sample``, ``merge``, ``score.sh`` under both venvs, ``dependency_flips``, ``recheck``,
   ``report``).
4. ``zinv`` (metric image): this addendum's guard, ``campaign guard``, ``run rescore`` over the
   run and the parent's control run of the split, then ``run judge``.

    zr_host.py plan --src SRC --name NAME --split reserve          # Q2ZR_PREREG_FROZEN exported
    zr_host.py plan --src SRC --name NAME --split dev --controls-run dev-controls-v9
    zr_host.py plan ... --split dev --controls-run dev-controls-v9 --reuse-parent-run dev-mutants-v9
    zr_host.py next --name NAME [--dry-run]                         # repeat until "complete"
    zr_host.py status --name NAME
    zr_host.py export --name NAME                                   # after "complete"

``export`` writes the release view of a complete plan to ``<run>/release/`` (registration
section 10): ``<run>/view/`` is a run root in the parent's layout (``prep``, ``build``,
``score`` and ``zinv`` link to the finished attempts; ``submitted.json`` has the parent's keys
and the finished jobs), the parent's own ``campaign export`` writes ``release/campaign/`` from
it, and the step outputs of this addendum (``zinv-rows.json`` with checker messages cut as the
parent cuts them, ``judgement.json``, ``targets-selection.json``), every receipt of every
attempt and the plan are copied beside it, with ``BLIND-WARNING.txt`` (the per-mutant verdict
files of ``campaign/`` carry no warning of their own), listed with their digests in
``manifest.json``.
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
ROOT = STAGE0 / "q2-zinv-reserve"
Q2M = STAGE0 / "q2-evaluator-mutation"
INPUTS = Q2M / "inputs"
LANE = "infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
PY = "/opt/venv-lock/bin/python"
PARENT_ID = "q2-evaluator-mutation-v1"
EXPERIMENT_ID = "q2-zinv-reserve-validation-v1"
FROZEN_ENV = "Q2ZR_PREREG_FROZEN"
FAMILY = "pptx"
WORKERS = 16  # the parent's mutation run
ZINV_WORKERS = 7  # the validated job 1000
TIMEOUT_S = 300
MAX_ATTEMPTS = 2
CAP_LANE_HOURS = 4.0
STAGES = ("targets", "build", "score", "zinv")
STAGE_DIRS = {"targets": "prep", "build": "build", "score": "score", "zinv": "zinv"}
RESOURCES = {  # cpus, memory, tmpfs, time limit (minutes; at least three times the projection)
    "targets": (4, "16G", "8g", 30),
    "build": (WORKERS, "96G", "32g", 60),
    "score": (WORKERS, "96G", "32g", 90),
    "zinv": (8, "32G", "16g", 60),
}
TERMINAL = ("done", "superseded", "failed_final")
VIEW_DIR = "view"
RELEASE_DIR = "release"
ERROR_HEAD = 80  # the parent's release_verdict: a checker message is cut to 80 characters


class HostError(RuntimeError):
    pass


# --- staged tree -------------------------------------------------------------------------


def check_src(src: Path) -> str:
    marker = src / ".git_sha"
    if not marker.is_file():
        raise HostError(f"{src} is not a staged export (no .git_sha)")
    return marker.read_text(encoding="utf-8").strip()


def load_staged(src: Path) -> tuple[Any, Any, Any]:
    """The staged tree's guard, rules and the parent's campaign module."""
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from harness.q2_mutation import campaign
    from harness.q2_zinv_reserve import guard, rules

    return guard, rules, campaign


def parent_pins(src: Path, campaign: Any) -> dict[str, Any]:
    return campaign.prereg_pins((src / campaign.PREREG_PATH).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_controls(split: str, controls: Path, rules: Any) -> None:
    for sub in ("saved", "lo"):
        if not (controls / sub).is_dir():
            raise HostError(f"no {controls / sub}")
    if split != rules.SPLIT:
        return
    for name, digest in rules.RESERVE_CONTROLS.items():
        if sha256_file(controls / "saved" / name) != digest:
            raise HostError(f"{controls / 'saved' / name} differs from its registered digest")


# --- commands ----------------------------------------------------------------------------


def parent_commands(split: str, workers: int, apply_to: str) -> tuple[str, str, str]:
    """The ``sh -c`` bodies of the parent's ``submit_mutants.sh`` jobs 1-3 (whitespace folded;
    ``tests/test_q2_zinv_reserve.py`` checks them against the frozen script)."""
    py = PY
    guard = f"cd /src && {py} -m harness.q2_mutation.campaign guard --split {split} --src /src --inputs /inputs"  # noqa: E501
    a1 = (
        f"{guard} && /src/infra/q2-mutation/run/make_jobs.sh {split} /out/jobs.jsonl"
        f" && cd /src && {py} -m harness.q2_mutation.campaign targets --src /src"
        f" --osworld /inputs/OSWorld --jobs /out/jobs.jsonl --split {split} --out /out"
    )
    a2 = (
        "cd /src && python3 -m harness.q2_mutation.campaign build"
        " --targets /ro/prep/targets.jsonl --out /out"
        f" --profile-template /home/user/.config/libreoffice/4/user --shards 8 --apply-to {apply_to}"  # noqa: E501
        f" && mkdir -p /out/lo && /src/infra/q2-mutation/run/reach.sh /out/scoring-jobs.jsonl /out/lo {workers}"  # noqa: E501
    )
    a3 = (
        f"{guard} && {py} -m harness.q2_mutation.campaign k2-sample"
        " --jobs /ro/build/scoring-jobs.jsonl --sanitized /src/program/evidence/q2-mutation/sanitized-tasks"  # noqa: E501
        " --out /out/k2-sample.jsonl"
        f" && {py} -m harness.q2_mutation.campaign merge"
        " --jobs /ro/build/scoring-jobs.jsonl --lo-rows $(ls /ro/build/lo/reachability-*.jsonl)"
        " --out /out/jobs-saved.jsonl --path-map /out/=/ro/build/"
        f" && /src/infra/q2-mutation/run/score.sh /out/jobs-saved.jsonl /out/mut {workers} 2"
        f" && {py} -m harness.q2_mutation.dependency_flips --jobs /out/jobs-saved.jsonl --prefix /out/mut"  # noqa: E501
        f" --workers {workers}"
        f" && {py} -m harness.q2_mutation.campaign recheck --mutations /ro/build/mutations.jsonl"
        " --admission /ro/build/admission.jsonl --saved-jobs /out/jobs-saved.jsonl --out /out/recheck.jsonl"  # noqa: E501
        f" && {py} -m harness.q2_mutation.campaign report --run /out --mutations /ro/build/mutations.jsonl"  # noqa: E501
        " --admission /ro/build/admission.jsonl"
        " --probe-touched /src/program/evidence/q2-mutation/harness/probe_touched.json"
    )
    return a1, a2, a3


def step_argv(stage: str, split: str, apply_to: str) -> list[str]:
    """The container argv of one step (the lane's ``Q2M_ARGV_JSON_HEX``)."""
    py = PY
    env = (
        []
        if split == "dev"
        else ["env", f"Q2M_PREREG_FROZEN={PARENT_ID}", f"{FROZEN_ENV}={EXPERIMENT_ID}"]
    )
    ours = f"cd /src && {py} -m harness.q2_zinv_reserve.guard check --split {split} --src /src"
    a1, a2, a3 = parent_commands(split, WORKERS, apply_to)
    if stage == "targets":
        select = (
            f"cd /src && {py} -m harness.q2_zinv_reserve.run select-targets"
            f" --prep /out --family {FAMILY} --split {split}"
        )
        return [*env, "sh", "-c", f"{ours} && {a1} && {select}"]
    if stage == "build":
        return ["sh", "-c", a2]
    if stage == "score":
        return [*env, "sh", "-c", f"{ours} && {a3}"]
    if stage == "zinv":
        q2guard = f"cd /src && {py} -m harness.q2_mutation.campaign guard --split {split} --src /src --inputs /inputs"  # noqa: E501
        rescore = (
            f"{py} -m harness.q2_zinv_reserve.run rescore --split {split}"
            " --mutant-jobs /ro/score/jobs-saved.jsonl --mutant-verdicts /ro/score/mut-verdicts-lock.jsonl"  # noqa: E501
            " --outcomes /ro/score/outcomes.jsonl --gold-jobs /ro/csaved/jobs-saved-mounted.jsonl"
            " --gold-verdicts /ro/csaved/saved-verdicts-lock.jsonl --osworld /inputs/OSWorld"
            " --file-cache /inputs/file_cache_1e112283/files --vm-baseline /inputs/vm-baseline"
            f" --out /out/zinv-rows.json --workers {ZINV_WORKERS} --timeout {TIMEOUT_S}"
        )
        judge = f"{py} -m harness.q2_zinv_reserve.run judge --rows /out/zinv-rows.json --out /out/judgement.json"  # noqa: E501
        return [*env, "sh", "-c", f"{ours} && {q2guard} && {rescore} && {judge}"]
    raise HostError(f"unknown stage {stage}")


def hexargv(argv: list[str]) -> str:
    return json.dumps(argv).encode().hex()


def done_dir(plan: dict[str, Any], stage: str) -> str:
    for step in plan["steps"]:
        if step["stage"] == stage and step["state"] == "done":
            return step["run_dir"]
    raise HostError(f"no finished {stage} step")


def extra_ro(plan: dict[str, Any], stage: str) -> list[str]:
    if stage == "targets":
        return []
    if stage == "build":
        return [f"{done_dir(plan, 'targets')}:/ro/prep"]
    if stage == "score":
        return [f"{done_dir(plan, 'build')}:/ro/build"]
    controls = plan["controls_dir"]
    return [
        f"{done_dir(plan, 'build')}:/ro/build",
        f"{done_dir(plan, 'score')}:/ro/score",
        f"{controls}/saved:/ro/csaved",
        f"{controls}/lo:/ro/lo",
    ]


def lane_command(plan: dict[str, Any], step: dict[str, Any]) -> list[str]:
    stage = step["stage"]
    cpus, memory, tmpfs, minutes = RESOURCES[stage]
    image = plan["images"]["lo_vm" if stage == "build" else "metric"]
    argv = step_argv(stage, plan["split"], plan["apply_to"])
    env = [
        "ALL",
        "Q2M_MODE=run",
        f"Q2M_IMAGE_ID={image}",
        f"Q2M_ARGV_JSON_HEX={hexargv(argv)}",
        f"Q2M_SOURCE={plan['src']}",
        f"Q2M_RUN_DIR={step['run_dir']}",
        f"Q2M_INPUTS={INPUTS}",
        f"Q2M_TMPFS_SIZE={tmpfs}",
    ]
    mounts = extra_ro(plan, stage)
    if mounts:
        env.append("Q2M_EXTRA_RO=" + "+".join(mounts))
    return [
        "sbatch",
        "--parsable",
        f"--job-name=q2zr-{plan['name']}-{step['name']}",
        f"--cpus-per-task={cpus}",
        f"--mem={memory}",
        f"--time={minutes // 60:02d}:{minutes % 60:02d}:00",
        f"--output={plan['root']}/slurm/slurm-%x-%j.out",
        "--export=" + ",".join(env),
        str(Path(plan["src"]) / LANE),
    ]


# --- queue and receipts ------------------------------------------------------------------


def queue_jobs() -> list[str]:
    out = subprocess.run(
        ["squeue", "-h", "-o", "%i %j %u %T"], capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def sbatch(command: list[str]) -> str:
    out = subprocess.run(command, capture_output=True, text=True)
    if out.returncode != 0:
        raise HostError(f"sbatch failed: {out.stderr.strip()}")
    return out.stdout.strip().split(";")[0]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def receipt_of(step: dict[str, Any]) -> dict[str, Any] | None:
    path = Path(step["run_dir"]) / f"receipt-{step['job']}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def step_finished(step: dict[str, Any], queue: list[str]) -> str | None:
    """done, failed, or None while the job is queued or running."""
    if any(line.split()[0] == step["job"] for line in queue):
        return None
    receipt = receipt_of(step)
    if receipt is not None:
        return "done" if receipt.get("exit_status") == 0 else "failed"
    return "failed"


def step_hours(step: dict[str, Any]) -> float:
    if not step.get("job"):
        return 0.0
    receipt = receipt_of(step)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    if receipt is not None:
        start, end = receipt["started_at"], receipt["finished_at"]
    elif step.get("submitted_at") and step.get("finished_seen_at"):
        start, end = step["submitted_at"], step["finished_seen_at"]
    else:
        return 0.0
    return (datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).total_seconds() / 3600


def hours_used(plan: dict[str, Any]) -> float:
    return sum(step_hours(s) for s in plan["steps"])


# --- plan --------------------------------------------------------------------------------


def run_root(root: Path, name: str) -> Path:
    return root / "runs" / name


def write_plan(run: Path, plan: dict[str, Any]) -> None:
    tmp = run / "plan.json.tmp"
    tmp.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(run / "plan.json")


def read_plan(root: Path, name: str) -> tuple[Path, dict[str, Any]]:
    run = run_root(root, name)
    return run, json.loads((run / "plan.json").read_text(encoding="utf-8"))


def make_plan(
    src: Path,
    name: str,
    split: str,
    controls_run: str | None,
    root: Path = ROOT,
    reuse_parent_run: str | None = None,
) -> dict[str, Any]:
    """A run plan. ``reuse_parent_run`` (dev only, a rehearsal of step 4) records steps 1-3 as
    done in an existing parent mutation run of the dev split, so only ``zinv`` is submitted."""
    if reuse_parent_run is not None and split != "dev":
        raise HostError("only a dev rehearsal may reuse a parent run")
    sha = check_src(src)
    guard, rules, campaign = load_staged(src)
    row = guard.require_split_allowed(split, src)
    pins = parent_pins(src, campaign)
    if split == rules.SPLIT:
        if name != rules.RESERVE_PLAN:
            raise HostError(f"the reserve split's one registered plan is {rules.RESERVE_PLAN}")
        if controls_run not in (None, rules.RESERVE_CONTROLS_RUN):
            raise HostError(f"the reserve split reads {rules.RESERVE_CONTROLS_RUN} only")
        controls_run = rules.RESERVE_CONTROLS_RUN
    elif not controls_run:
        raise HostError("name the dev split's control run (--controls-run)")
    controls = Q2M / "runs" / controls_run
    check_controls(split, controls, rules)
    run = run_root(root, name)
    if run.exists():
        raise HostError(f"{run} exists; version the run name")
    steps = [
        {
            "name": stage,
            "stage": stage,
            "attempt": 1,
            "run_dir": str(run / STAGE_DIRS[stage]),
            "state": "pending",
            "job": None,
        }
        for stage in STAGES
    ]
    if reuse_parent_run is not None:
        parent_run = Q2M / "runs" / reuse_parent_run
        submitted = json.loads((parent_run / "submitted.json").read_text(encoding="utf-8"))
        if submitted.get("split") != "dev":
            raise HostError(f"{parent_run} is not a dev-split mutation run")
        for step in steps[:3]:
            step["run_dir"] = str(parent_run / STAGE_DIRS[step["stage"]])
            step["state"] = "done"
            step["reused"] = reuse_parent_run
    return {
        "experiment_id": EXPERIMENT_ID,
        "name": name,
        "split": split,
        "git_sha": sha,
        "src": str(src),
        "root": str(root),
        "frozen_ledger_hash": (row or {}).get("hash"),
        "controls_run": controls_run,
        "controls_dir": str(controls),
        "images": {"metric": pins["metric_image_id"], "lo_vm": pins["lo_vm_image_id"]},
        "apply_to": pins["apply_to"],
        "family": FAMILY,
        "cap_lane_hours": CAP_LANE_HOURS,
        "reuse_parent_run": reuse_parent_run,
        "created_at": now(),
        "steps": steps,
    }


def cmd_plan(args: argparse.Namespace) -> None:
    plan = make_plan(
        args.src.resolve(), args.name, args.split, args.controls_run, args.root,
        args.reuse_parent_run,
    )  # fmt: skip
    run = run_root(args.root, args.name)
    run.mkdir(parents=True)
    (args.root / "slurm").mkdir(parents=True, exist_ok=True)
    write_plan(run, plan)
    print(json.dumps({k: plan[k] for k in ("name", "split", "git_sha", "controls_run")}))


def handle_failure(plan: dict[str, Any], index: int) -> str:
    step = plan["steps"][index]
    if step["attempt"] >= MAX_ATTEMPTS:
        step["state"] = "failed_final"
        return "failed_final"
    retry = copy.deepcopy(step)
    retry["attempt"] = step["attempt"] + 1
    retry["run_dir"] = f"{step['run_dir'].rsplit('.a', 1)[0]}.a{retry['attempt']}"
    retry["name"] = f"{step['stage']}.a{retry['attempt']}"
    for key in ("job", "submitted_at", "finished_seen_at", "command"):
        retry[key] = None
    retry["state"] = "pending"
    step["state"] = "superseded"
    plan["steps"].insert(index + 1, retry)
    return "retry"


def recheck_before_submit(plan: dict[str, Any], step: dict[str, Any]) -> None:
    src = Path(plan["src"])
    if check_src(src) != plan["git_sha"]:
        raise HostError("the staged export changed since the plan")
    guard, rules, _campaign = load_staged(src)
    guard.require_split_allowed(plan["split"], src)
    if step["stage"] == "zinv":
        check_controls(plan["split"], Path(plan["controls_dir"]), rules)


def cmd_next(args: argparse.Namespace) -> None:
    run, plan = read_plan(args.root, args.name)
    queue = queue_jobs()
    index = 0
    while index < len(plan["steps"]):
        step = plan["steps"][index]
        if step["state"] in TERMINAL:
            if step["state"] == "failed_final":
                write_plan(run, plan)
                print(json.dumps({"state": "failed_final", "step": step["name"]}))
                return
            index += 1
            continue
        if step["state"] == "submitted":
            result = step_finished(step, queue)
            if result is None:
                print(json.dumps({"state": "running", "step": step["name"], "job": step["job"]}))
                return
            step["state"] = result
            step["finished_seen_at"] = now()
        if step["state"] == "failed":
            outcome = handle_failure(plan, index)
            write_plan(run, plan)
            print(json.dumps({"failed": step["name"], "job": step["job"], "then": outcome}))
            if outcome == "failed_final":
                return
            index += 1
            continue
        if step["state"] == "done":
            write_plan(run, plan)
            index += 1
            continue
        used = hours_used(plan)
        if used >= plan["cap_lane_hours"]:
            print(json.dumps({"state": "cap_reached", "hours_used": round(used, 3)}))
            return
        recheck_before_submit(plan, step)
        command = lane_command(plan, step)
        if args.dry_run:
            argv = step_argv(step["stage"], plan["split"], plan["apply_to"])
            print(json.dumps({"state": "dry_run", "step": step["name"], "queue": queue,
                              "argv": argv, "sbatch": command}, indent=1))  # fmt: skip
            return
        if queue:
            print(json.dumps({"state": "waiting_for_queue", "step": step["name"], "queue": queue}))
            return
        Path(step["run_dir"]).mkdir(parents=True, exist_ok=False)
        step["command"] = command
        step["job"] = sbatch(command)
        step["state"] = "submitted"
        step["submitted_at"] = now()
        write_plan(run, plan)
        print(json.dumps({"state": "submitted", "step": step["name"], "job": step["job"]}))
        return
    write_plan(run, plan)
    print(json.dumps({"state": "complete", "name": plan["name"], "hours_used": hours_used(plan)}))


def cmd_status(args: argparse.Namespace) -> None:
    _run, plan = read_plan(args.root, args.name)
    out: dict[str, Any] = {
        "name": plan["name"],
        "split": plan["split"],
        "hours_used": round(hours_used(plan), 3),
        "cap_lane_hours": plan["cap_lane_hours"],
        "steps": [
            {k: s.get(k) for k in ("name", "state", "job", "run_dir")} for s in plan["steps"]
        ],
    }
    zinv = [s for s in plan["steps"] if s["stage"] == "zinv" and s["state"] == "done"]
    if zinv:
        judgement = json.loads((Path(zinv[0]["run_dir"]) / "judgement.json").read_text())
        out["judgement"] = {k: judgement[k] for k in ("outcome", "status", "fail_reasons")}
    print(json.dumps(out, indent=1))


# --- release view ------------------------------------------------------------------------


def finished_steps(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The finished attempt of every stage; refuses a plan that is not complete."""
    done: dict[str, dict[str, Any]] = {}
    for step in plan["steps"]:
        if step["state"] == "done":
            done[step["stage"]] = step
        elif step["state"] != "superseded":
            raise HostError(f"step {step['name']} is {step['state']}: the plan is not complete")
    missing = [stage for stage in STAGES if stage not in done]
    if missing:
        raise HostError(f"no finished step for {missing}")
    return done


def make_view(run: Path, plan: dict[str, Any]) -> Path:
    """``<run>/view``: a run root in the parent's layout for its ``campaign export``."""
    if plan.get("reuse_parent_run"):
        raise HostError("a plan that reuses a parent run is released by that run's export")
    done = finished_steps(plan)
    submitted = {
        "run": plan["name"],
        "split": plan["split"],
        "git_sha": plan["git_sha"],
        "apply_to": plan["apply_to"],
        "jobs": [int(done[stage]["job"]) for stage in STAGES],
        "superseded_jobs": [
            int(s["job"]) for s in plan["steps"] if s["state"] == "superseded" and s.get("job")
        ],
        "experiment_id": EXPERIMENT_ID,
    }
    links = {STAGE_DIRS[stage]: done[stage]["run_dir"] for stage in STAGES}
    view = run / VIEW_DIR
    if view.exists():
        current = json.loads((view / "submitted.json").read_text(encoding="utf-8"))
        if current != submitted or any(
            os.readlink(view / name) != target for name, target in links.items()
        ):
            raise HostError(f"{view} exists and differs from the plan")
        return view
    view.mkdir()
    for name, target in links.items():
        os.symlink(target, view / name)
    (view / "submitted.json").write_text(json.dumps(submitted, sort_keys=True) + "\n")
    return view


def release_rows(data: dict[str, Any]) -> dict[str, Any]:
    """The rows file with every checker message cut to the parent's release length."""
    out = copy.deepcopy(data)
    for row in out.get("rows", []):
        for key in ("raw_error", "zinv_error"):
            head = row.get(key)
            if isinstance(head, str) and len(head) > ERROR_HEAD:
                row[key] = head[:ERROR_HEAD] + "..."
    return out


def write_json(path: Path, data: Any) -> None:
    """``run.write_json``'s format, so an unchanged rows file keeps its bytes."""
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def export_release(root: Path, name: str) -> dict[str, Any]:
    run, plan = read_plan(root, name)
    src = Path(plan["src"])
    if check_src(src) != plan["git_sha"]:
        raise HostError("the staged export changed since the plan")
    guard, rules, campaign = load_staged(src)
    guard.require_split_allowed(plan["split"], src)
    final = run / RELEASE_DIR
    if final.exists():
        raise HostError(f"{final} exists; the release view is written once")
    view = make_view(run, plan)
    done = finished_steps(plan)
    if plan["split"] != "dev":  # the parent's export re-checks its own frozen row and pins
        os.environ["Q2M_PREREG_FROZEN"] = PARENT_ID
    out = run / f"{RELEASE_DIR}.partial"  # an interrupted export leaves only this behind
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    code = campaign.main(
        ["export", "--run", str(view), "--out", str(out / "campaign"), "--src", str(src)]
    )
    if code != 0:
        raise HostError("the parent's campaign export refused the view")
    zinv_dir, prep_dir = Path(done["zinv"]["run_dir"]), Path(done["targets"]["run_dir"])
    rows = json.loads((zinv_dir / "zinv-rows.json").read_text(encoding="utf-8"))
    write_json(out / "zinv-rows.json", release_rows(rows))
    for source in (zinv_dir / "judgement.json", prep_dir / "targets-selection.json"):
        (out / source.name).write_bytes(source.read_bytes())
    (out / "receipts").mkdir()
    for step in plan["steps"]:
        receipt = Path(step["run_dir"]) / f"receipt-{step['job']}.json"
        if step.get("job") and receipt.is_file():
            target = out / "receipts" / f"{step['name']}-receipt-{step['job']}.json"
            target.write_bytes(receipt.read_bytes())
    (out / "plan.json").write_bytes((run / "plan.json").read_bytes())
    # campaign/ holds the parent's per-mutant verdict files, which carry no warning of their own
    (out / "BLIND-WARNING.txt").write_text(rules.BLIND_WARNING + "\n", encoding="utf-8")
    files = {
        path.relative_to(out).as_posix(): sha256_file(path)
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }
    judgement = json.loads((out / "judgement.json").read_text(encoding="utf-8"))
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "name": plan["name"],
        "split": plan["split"],
        "git_sha": plan["git_sha"],
        "frozen_ledger_hash": plan.get("frozen_ledger_hash"),
        "warning": rules.BLIND_WARNING,
        "outcome": judgement.get("outcome"),
        "status": judgement.get("status"),
        "zinv_rows_sha256_on_host": sha256_file(zinv_dir / "zinv-rows.json"),
        "files_sha256": files,
    }
    write_json(out / "manifest.json", manifest)
    out.rename(final)
    return {"release": str(final), "files": len(files) + 1, "outcome": manifest["outcome"]}


def cmd_export(args: argparse.Namespace) -> None:
    print(json.dumps(export_release(args.root, args.name)))


def main(argv: list[str] | None = None) -> int:
    os.umask(0o022)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--src", type=Path, required=True)
    pl.add_argument("--name", required=True)
    pl.add_argument("--split", required=True, choices=["dev", "reserve"])
    pl.add_argument("--controls-run", default=None)
    pl.add_argument("--reuse-parent-run", default=None, help="dev only: rehearse step 4 alone")
    nx = sub.add_parser("next")
    nx.add_argument("--name", required=True)
    nx.add_argument("--dry-run", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("--name", required=True)
    ex = sub.add_parser("export", help="the release view of a complete plan (section 10)")
    ex.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    commands = {"plan": cmd_plan, "next": cmd_next, "status": cmd_status, "export": cmd_export}
    try:
        commands[args.command](args)
    except HostError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - the staged guard's refusals
        if type(exc).__name__ in ("GuardError", "CampaignError"):
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
