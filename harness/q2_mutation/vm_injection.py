"""Corrected in-VM injection protocol for the Q2 fidelity gate (design + plan).

The scoping plan injected a mutant onto disk while LibreOffice still held the
original document, so the postconfig Ctrl+S overwrote the mutant with the
in-memory original and every mutant scored as do-nothing. The corrected
protocol places the candidate before the application opens the document:

1. reset the VM to the task snapshot and run the task's own config (OSWorld
   ``reset``), so the VM is in the task's initial state;
2. close every application that holds a target file (``pkill`` the process,
   then confirm no window title names the file);
3. hash each target path in the VM (``pre_inject``);
4. upload each candidate file to its VM path through the same server
   endpoint the task's download step uses, then hash it again in the VM and
   require it to equal the candidate's local SHA-256 (``post_inject``);
5. re-run the task's own ``open``/``launch`` config steps for those files and
   wait for the window, exactly as the task setup does;
6. hash the targets (``pre_postconfig``), run the evaluator's postconfig
   verbatim, hash again (``post_postconfig``) and log whether the save wrote;
7. call the real ``DesktopEnv.evaluate()`` over the VM and record the score;
8. compare with the offline harness verdict for the same candidate (same
   ``candidate_sha256``) and record agreement per checker family.

This module only produces the step plan and checks its invariants; the VM
runtime (``stage0/q2-action-path``) executes it later. The plan is data, so the
fidelity gate is reproducible and reviewable before it runs.
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping, Sequence
from typing import Any

from harness.q2_mutation.tasks import resolve_vm_path

APP_PROCESSES = {
    ".docx": "soffice",
    ".doc": "soffice",
    ".odt": "soffice",
    ".xlsx": "soffice",
    ".xls": "soffice",
    ".ods": "soffice",
    ".csv": "soffice",
    ".pptx": "soffice",
    ".ppt": "soffice",
    ".odp": "soffice",
    ".png": "gimp",
    ".jpg": "gimp",
    ".jpeg": "gimp",
    ".xcf": "gimp",
}


class InjectionPlanError(ValueError):
    pass


def _reopen_steps(raw: Mapping[str, Any], targets: Sequence[str]) -> list[dict[str, Any]]:
    """The task's own open/launch steps that refer to a target file."""
    names = {posixpath.basename(t) for t in targets}
    steps: list[dict[str, Any]] = []
    for step in raw.get("config", []):
        kind = step.get("type")
        params = step.get("parameters", {})
        if kind == "open" and resolve_vm_path(str(params.get("path", ""))) in targets:
            steps.append({"op": "config_step", "step": step})
        elif kind == "launch":
            command = params.get("command")
            text = " ".join(command) if isinstance(command, list) else str(command)
            if any(name in text for name in names):
                steps.append({"op": "config_step", "step": step})
    return steps


def build_injection_plan(
    raw: Mapping[str, Any], candidate: Mapping[str, Mapping[str, str]], candidate_sha256: str
) -> list[dict[str, Any]]:
    """Ordered steps for one (task, candidate) pair.

    ``candidate`` maps VM path -> {"local": host path, "sha256": hex}.
    """
    if not candidate:
        raise InjectionPlanError("empty candidate")
    targets = sorted(resolve_vm_path(path) for path in candidate)
    processes = sorted(
        {
            APP_PROCESSES[ext]
            for ext in (posixpath.splitext(t)[1].lower() for t in targets)
            if ext in APP_PROCESSES
        }
    )
    plan: list[dict[str, Any]] = [{"op": "reset_task", "task_id": raw["id"]}]
    for process in processes:
        plan.append({"op": "kill_process", "name": process})
    plan.append(
        {"op": "assert_no_window", "titles_containing": [posixpath.basename(t) for t in targets]}
    )
    plan.append({"op": "hash", "tag": "pre_inject", "paths": targets})
    for path in targets:
        info = candidate[path] if path in candidate else candidate[_original_key(candidate, path)]
        plan.append(
            {"op": "upload", "path": path, "local": info["local"], "sha256": info["sha256"]}
        )
    plan.append({"op": "hash", "tag": "post_inject", "paths": targets, "expect": "candidate"})
    reopen = _reopen_steps(raw, targets)
    plan += reopen
    plan.append({"op": "hash", "tag": "pre_postconfig", "paths": targets})
    plan.append({"op": "postconfig", "steps": list(raw.get("evaluator", {}).get("postconfig", []))})
    plan.append({"op": "hash", "tag": "post_postconfig", "paths": targets})
    plan.append({"op": "evaluate", "candidate_sha256": candidate_sha256})
    check_plan(plan)
    return plan


def _original_key(candidate: Mapping[str, Any], resolved: str) -> str:
    for key in candidate:
        if resolve_vm_path(key) == resolved:
            return key
    raise InjectionPlanError(f"no candidate entry for {resolved}")


def check_plan(plan: Sequence[Mapping[str, Any]]) -> None:
    """Invariants the scoping protocol violated, checked on every plan."""
    ops = [step["op"] for step in plan]

    def first(op: str) -> int:
        return ops.index(op)

    def last(op: str) -> int:
        return len(ops) - 1 - ops[::-1].index(op)

    if ops[0] != "reset_task":
        raise InjectionPlanError("plan must start from the task's reset state")
    if "upload" not in ops:
        raise InjectionPlanError("plan uploads nothing")
    kills = [i for i, op in enumerate(ops) if op == "kill_process"]
    if kills and max(kills) > first("upload"):
        raise InjectionPlanError("an application is killed after the candidate is placed")
    if first("assert_no_window") > first("upload"):
        raise InjectionPlanError("files are replaced while a window may still hold them")
    reopen = [i for i, op in enumerate(ops) if op == "config_step"]
    if reopen and min(reopen) < last("upload"):
        raise InjectionPlanError("a document is reopened before every candidate is placed")
    if not first("postconfig") > last("upload"):
        raise InjectionPlanError("postconfig must run after injection")
    tags = [step.get("tag") for step in plan if step["op"] == "hash"]
    if tags != ["pre_inject", "post_inject", "pre_postconfig", "post_postconfig"]:
        raise InjectionPlanError(f"hash checkpoints out of order: {tags}")
    if ops[-1] != "evaluate":
        raise InjectionPlanError("plan must end with evaluate")
