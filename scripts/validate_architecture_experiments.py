#!/usr/bin/env python3
"""Validate architecture-research contracts without pretending they are runnable."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry  # noqa: E402

DEFAULT_CONTRACT_ROOT = PROJECT_ROOT / "experiments" / "architectures"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DIGEST_IMAGE_RE = re.compile(r"^[^\s]+@sha256:[0-9a-f]{64}$")
CLAIM_SCOPES = {
    "attachment-capability",
    "architecture-causal",
    "portability-protocol",
    "systems-pipeline",
}
ARM_MODES = {
    "frozen-checkpoint-retrofit",
    "continued-pretraining-retrofit",
    "checkpoint-finetune",
    "matched-from-scratch",
}


def mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return {}
    return value


def nonempty_string(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def validate_contract(payload: Any, known_models: set[str]) -> list[str]:
    errors: list[str] = []
    contract = mapping(payload, "contract", errors)
    if contract.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    name = contract.get("name")
    if not isinstance(name, str) or not SLUG_RE.fullmatch(name):
        errors.append("name must be kebab-case")
    nonempty_string(contract.get("direction"), "direction", errors)
    question = contract.get("research_question")
    if not isinstance(question, str) or len(question.strip()) < 30:
        errors.append("research_question must state a concrete question (>=30 characters)")
    nonempty_string(contract.get("null_hypothesis"), "null_hypothesis", errors)

    for section_name in ("stage0_reference", "reference_doctor"):
        if section_name not in contract:
            continue
        reference = mapping(contract.get(section_name), section_name, errors)
        implementation = reference.get("implementation")
        if not isinstance(implementation, str) or not implementation.strip():
            errors.append(f"{section_name}.implementation must be a non-empty path")
        else:
            implementation_path = (PROJECT_ROOT / implementation).resolve()
            if (
                PROJECT_ROOT not in implementation_path.parents
                or not implementation_path.is_file()
            ):
                errors.append(f"{section_name}.implementation must exist in the repo")
        command = reference.get("command_argv")
        if (
            not isinstance(command, list)
            or len(command) < 4
            or not all(isinstance(part, str) and part for part in command)
        ):
            errors.append(f"{section_name}.command_argv must be a non-empty argv list")
        elif command[:3] != ["uv", "run", "python"]:
            errors.append(f"{section_name}.command_argv must use uv run python")
        elif not (PROJECT_ROOT / command[3]).is_file():
            errors.append(f"{section_name}.command_argv script must exist")

    readiness = contract.get("readiness")
    if readiness not in {"contract", "pilot-ready"}:
        errors.append("readiness must be contract or pilot-ready")
    claim_scope = contract.get("claim_scope")
    if claim_scope not in CLAIM_SCOPES:
        errors.append(f"claim_scope must be one of {sorted(CLAIM_SCOPES)}")

    starting = mapping(contract.get("starting_point"), "starting_point", errors)
    arms = starting.get("arms")
    modes: set[str] = set()
    referenced_models: set[str] = set()
    control_arms = 0
    if not isinstance(arms, list) or len(arms) < 2:
        errors.append("starting_point.arms must contain at least two arms")
    else:
        arm_names: set[str] = set()
        for index, raw_arm in enumerate(arms):
            arm = mapping(raw_arm, f"starting_point.arms[{index}]", errors)
            arm_name = arm.get("name")
            if not isinstance(arm_name, str) or not SLUG_RE.fullmatch(arm_name):
                errors.append(f"starting_point.arms[{index}].name must be kebab-case")
            elif arm_name in arm_names:
                errors.append(f"duplicate arm name: {arm_name}")
            else:
                arm_names.add(arm_name)
            mode = arm.get("mode")
            if mode not in ARM_MODES:
                errors.append(f"starting_point.arms[{index}].mode is invalid")
            else:
                modes.add(mode)
            model_ids = arm.get("model_ids")
            if not isinstance(model_ids, list):
                errors.append(f"starting_point.arms[{index}].model_ids must be a list")
            else:
                for model_id in model_ids:
                    if model_id not in known_models:
                        errors.append(f"unknown model id in arm {arm_name}: {model_id!r}")
                    elif isinstance(model_id, str):
                        referenced_models.add(model_id)
            if arm.get("is_control") is True:
                control_arms += 1
            nonempty_string(arm.get("purpose"), f"starting_point.arms[{index}].purpose", errors)
    if not referenced_models:
        errors.append("at least one registered model must be referenced")
    if claim_scope == "architecture-causal" and "matched-from-scratch" not in modes:
        errors.append("architecture-causal claims require a matched-from-scratch arm")
    if claim_scope == "architecture-causal" and control_arms == 0:
        errors.append("architecture-causal claims require a from-scratch control arm")
    if claim_scope == "attachment-capability" and "matched-from-scratch" in modes:
        errors.append("attachment-capability contracts must not mix in a causal architecture claim")
    if claim_scope == "portability-protocol" and len(referenced_models) < 2:
        errors.append("portability-protocol contracts require at least two registered bases")

    intervention = mapping(contract.get("intervention"), "intervention", errors)
    for field in ("mechanism", "trainable_components", "frozen_components"):
        value = intervention.get(field)
        if field == "mechanism":
            nonempty_string(value, f"intervention.{field}", errors)
        elif not isinstance(value, list) or not value:
            errors.append(f"intervention.{field} must be a non-empty list")

    data = mapping(contract.get("data"), "data", errors)
    for split_name in ("train", "development", "test"):
        split = mapping(data.get(split_name), f"data.{split_name}", errors)
        nonempty_string(split.get("source"), f"data.{split_name}.source", errors)
        nonempty_string(split.get("identity"), f"data.{split_name}.identity", errors)
        if split_name == "test" and split.get("sealed") is not True:
            errors.append("data.test.sealed must be true")
    checks = data.get("contamination_checks")
    if not isinstance(checks, list) or len(checks) < 2:
        errors.append("data.contamination_checks must contain at least two checks")

    controls = contract.get("controls")
    if not isinstance(controls, list) or len(controls) < 2:
        errors.append("controls must contain at least two matched controls")
    else:
        for index, raw_control in enumerate(controls):
            control = mapping(raw_control, f"controls[{index}]", errors)
            nonempty_string(control.get("name"), f"controls[{index}].name", errors)
            matches = control.get("matches")
            if not isinstance(matches, list) or len(matches) < 2:
                errors.append(f"controls[{index}].matches must name at least two matched axes")

    endpoint = mapping(contract.get("primary_endpoint"), "primary_endpoint", errors)
    for field in ("metric", "unit_of_analysis", "aggregation"):
        nonempty_string(endpoint.get(field), f"primary_endpoint.{field}", errors)
    if endpoint.get("direction") not in {"maximize", "minimize"}:
        errors.append("primary_endpoint.direction must be maximize or minimize")
    minimum_effect = endpoint.get("minimum_effect")
    if (
        not isinstance(minimum_effect, (int, float))
        or isinstance(minimum_effect, bool)
        or not math.isfinite(minimum_effect)
        or minimum_effect <= 0
    ):
        errors.append("primary_endpoint.minimum_effect must be finite and positive")

    statistics = mapping(contract.get("statistics"), "statistics", errors)
    seeds = statistics.get("seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) < 3
        or len(set(seeds)) != len(seeds)
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
    ):
        errors.append("statistics.seeds must contain at least three distinct integers")
    for field in ("interval", "multiplicity"):
        nonempty_string(statistics.get(field), f"statistics.{field}", errors)

    falsifiers = contract.get("falsifiers")
    if not isinstance(falsifiers, list) or len(falsifiers) < 2:
        errors.append("falsifiers must contain at least two explicit kill conditions")
    artifacts = contract.get("required_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) < 4:
        errors.append("required_artifacts must contain at least four outputs")

    execution = mapping(contract.get("execution"), "execution", errors)
    enabled = execution.get("enabled")
    if not isinstance(enabled, bool):
        errors.append("execution.enabled must be boolean")
    gpu_hours = execution.get("max_gpu_hours")
    if (
        not isinstance(gpu_hours, (int, float))
        or isinstance(gpu_hours, bool)
        or not math.isfinite(gpu_hours)
        or gpu_hours <= 0
        or gpu_hours > 64
    ):
        errors.append("execution.max_gpu_hours must be finite, positive, and <=64")
    gpus = execution.get("gpus")
    if not isinstance(gpus, int) or isinstance(gpus, bool) or not 1 <= gpus <= 8:
        errors.append("execution.gpus must be an integer from 1 through 8")
    if execution.get("checkpoint_to_persistent_storage") is not True:
        errors.append("execution.checkpoint_to_persistent_storage must be true")
    if execution.get("fresh_job_resume_test") is not True:
        errors.append("execution.fresh_job_resume_test must be true")
    if enabled or readiness == "pilot-ready":
        image = execution.get("container_image")
        if not isinstance(image, str) or not DIGEST_IMAGE_RE.fullmatch(image):
            errors.append("enabled/pilot-ready contracts require a digest-pinned container_image")
        argv = execution.get("command_argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
            errors.append("enabled/pilot-ready contracts require command_argv")
        receipts = execution.get("model_receipts")
        if not isinstance(receipts, list) or len(receipts) < len(referenced_models):
            errors.append("enabled/pilot-ready contracts require model receipts")
    else:
        blockers = execution.get("blocked_by")
        if not isinstance(blockers, list) or not blockers:
            errors.append("disabled contracts must state execution.blocked_by")

    return errors


def iter_contracts(paths: list[Path]) -> list[Path]:
    if paths:
        return paths
    return sorted(DEFAULT_CONTRACT_ROOT.glob("*.yaml"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    known_models = set(load_registry(args.registry.resolve())["models"])
    paths = iter_contracts(args.paths)
    if not paths:
        print("ERROR: no architecture experiment contracts found", file=sys.stderr)
        return 2

    failed = False
    for path in paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors = validate_contract(payload, known_models)
        if errors:
            failed = True
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            readiness = payload["readiness"]
            state = "RUNNABLE" if payload["execution"]["enabled"] else "BLOCKED"
            print(f"PASS {path} ({readiness}, {state})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
