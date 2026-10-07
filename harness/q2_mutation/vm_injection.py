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
6. open, in LibreOffice, every office target the postconfig saves but no
   config step opens (an agent-created output: absent from the initial
   state, so no task step opens it), and wait for its window
   (``open_file``); give every office target that no postconfig saves one
   agent-equivalent save (``agent_save``: open if needed, activate,
   Ctrl+S, wait for the write). This is the offline save stage's plan
   (``reachability.build_plan``: ``open_before_postconfig`` and
   ``agent_saves``), so both paths save the same files;
7. hash the targets (``pre_postconfig``), run the evaluator's postconfig
   verbatim, hash again (``post_postconfig``; every postconfig-saved target
   must have changed) and log whether the save wrote;
8. call the real ``DesktopEnv.evaluate()`` over the VM and record the score;
9. compare with the offline harness verdict for the same candidate (same
   ``candidate_sha256``) and record agreement per checker family and per
   save path (``save_paths`` on the evaluate step: postconfig_save,
   agent_save or no_save).

Op contract for the VM runtime (``stage0/q2-action-path``): ``open_file``
{path, window} launches LibreOffice on the path and waits for a window whose
title names the file; ``agent_save`` {path, window} does the same if no such
window exists, activates it, sends Ctrl+S and waits until the file's mtime
changes; ``hash`` with ``expect_changed`` fails the run if a listed path's
hash equals its ``pre_postconfig`` hash.

This module only produces the step plan and checks its invariants; the VM
runtime (``stage0/q2-action-path``) executes it later. The plan is data, so the
fidelity gate is reproducible and reviewable before it runs.
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping, Sequence
from typing import Any

from harness.q2_mutation.reachability import build_plan, window_title_for
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
    """The task's own open/launch steps that refer to a target file, with the targets each opens."""
    steps: list[dict[str, Any]] = []
    for step in raw.get("config", []):
        if step.get("type") not in ("open", "launch"):
            continue
        opens = [path for path in targets if _step_opens(step, path)]
        if opens:
            steps.append({"op": "config_step", "step": step, "opens": opens})
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
    saves = build_plan(raw, targets)
    reopened = {path for step in reopen for path in step["opens"]}
    for path in saves["agent_saves"]:
        plan.append({"op": "agent_save", "path": path, "window": window_title_for(path)})
    for path in saves["open_before_postconfig"]:
        if path not in reopened:
            plan.append({"op": "open_file", "path": path, "window": window_title_for(path)})
    plan.append({"op": "hash", "tag": "pre_postconfig", "paths": targets})
    plan.append({"op": "postconfig", "steps": list(raw.get("evaluator", {}).get("postconfig", []))})
    plan.append(
        {
            "op": "hash",
            "tag": "post_postconfig",
            "paths": targets,
            "expect_changed": list(saves["open_before_postconfig"]),
        }
    )
    plan.append(
        {
            "op": "evaluate",
            "candidate_sha256": candidate_sha256,
            "save_paths": {path: save_path(path, saves) for path in targets},
        }
    )
    check_plan(plan)
    return plan


def _step_opens(step: Mapping[str, Any], path: str) -> bool:
    params = step.get("parameters", {})
    if step.get("type") == "open":
        return resolve_vm_path(str(params.get("path", ""))) == path
    command = params.get("command")
    text = " ".join(command) if isinstance(command, list) else str(command)
    return posixpath.basename(path) in text


def save_path(path: str, saves: Mapping[str, Any]) -> str:
    """How a target reaches the checker: postconfig_save, agent_save or no_save."""
    if path in saves["open_before_postconfig"]:
        return "postconfig_save"
    if path in saves["agent_saves"]:
        return "agent_save"
    return "no_save"


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
    for op in ("open_file", "agent_save"):
        placed = [i for i, name in enumerate(ops) if name == op]
        if placed and (min(placed) < last("upload") or max(placed) > first("postconfig")):
            raise InjectionPlanError(f"{op} must run after injection and before postconfig")
    opened = {step["path"] for step in plan if step["op"] == "open_file"}
    opened |= {path for step in plan if step["op"] == "config_step" for path in step["opens"]}
    agent_saved = {step["path"] for step in plan if step["op"] == "agent_save"}
    for path, how in (plan[-1].get("save_paths") or {}).items():
        if how == "agent_save" and path not in agent_saved:
            raise InjectionPlanError(f"{path}: no agent-equivalent save")
        if how == "postconfig_save" and path not in opened:
            raise InjectionPlanError(f"{path}: the postconfig saves a document nothing opened")
    tags = [step.get("tag") for step in plan if step["op"] == "hash"]
    if tags != ["pre_inject", "post_inject", "pre_postconfig", "post_postconfig"]:
        raise InjectionPlanError(f"hash checkpoints out of order: {tags}")
    if ops[-1] != "evaluate":
        raise InjectionPlanError("plan must end with evaluate")
