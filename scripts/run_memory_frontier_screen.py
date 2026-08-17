#!/usr/bin/env python3
"""Run a bounded, single-arm memory screen against one hosted frontier model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

import yaml
from scipy.stats import fisher_exact

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import TrialPlan  # noqa: E402
from harness.memory_trials import (  # noqa: E402
    AnthropicMessagesCompletion,
    AnthropicMessagesConfig,
    CompletionResult,
    FrozenMemorySystem,
    GeminiGenerateContentCompletion,
    GeminiGenerateContentConfig,
    GeneratedMemoryTaskSource,
    GeneratedSafetyMemoryTaskSource,
    JsonCompletionMemoryActor,
    MemoryBudget,
    OpenAICompatibleCompletion,
    OpenAICompatibleConfig,
    OpenAIResponsesCompletion,
    OpenAIResponsesConfig,
    ReplayableMemoryWorld,
    collect_resumable,
    task_manifest_sha256,
)
from scripts.run_memory_model_screen import summarize_screen  # noqa: E402
from scripts.run_memory_trials import ALLOWED_FEATURES  # noqa: E402
from scripts.validate_provider_models import (  # noqa: E402
    DEFAULT_REGISTRY,
    load_provider_registry,
)


class ProviderBackend(Protocol):
    identity: str

    def complete(self, prompt: str) -> CompletionResult: ...

    def preflight(self) -> Mapping[str, str | int | bool]: ...


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)
    return hashlib.sha256(encoded).hexdigest()


def _source_receipt() -> dict[str, Any]:
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    bound_files = (
        PROJECT_ROOT / "harness" / "causal_memory_trials.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "collection.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "engine.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "frozen.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "frontier_providers.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "models.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "openai_compatible.py",
        PROJECT_ROOT / "harness" / "memory_trials" / "systems.py",
        Path(__file__).resolve(),
    )
    return {
        "git_sha": git_sha,
        "dirty": bool(status),
        "changed_paths_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "working_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "bound_files": {
            str(path.relative_to(PROJECT_ROOT)): _sha256_file(path)
            for path in bound_files
        },
    }


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("stage") != "model_transport"
    ):
        raise ValueError("frontier screen requires a stage: model_transport contract")
    return payload


def _allowed_provider_models(config: Mapping[str, Any]) -> set[str]:
    model = config.get("model")
    if not isinstance(model, dict):
        raise ValueError("model transport contract has no model section")
    roster = model.get("provider_roster")
    if not isinstance(roster, list) or not all(isinstance(item, str) for item in roster):
        raise ValueError("provider_roster must be a list of model ids")
    allowed = set(roster)
    secondary = model.get("maximum_capability_secondary")
    if isinstance(secondary, str):
        allowed.add(secondary)
    return allowed


def build_provider_backend(
    entry: Mapping[str, Any],
    *,
    max_completion_tokens: int,
) -> ProviderBackend:
    provider = str(entry["provider"])
    model_id = str(entry["model_id"])
    api_key_env = str(entry["api_key_env"])
    if provider == "openai":
        return OpenAIResponsesCompletion(
            OpenAIResponsesConfig(
                model_id=model_id,
                api_key_env=api_key_env,
                max_output_tokens=max_completion_tokens,
                reasoning_effort="none",
            )
        )
    if provider == "anthropic":
        return AnthropicMessagesCompletion(
            AnthropicMessagesConfig(
                model_id=model_id,
                api_key_env=api_key_env,
                max_tokens=max_completion_tokens,
            )
        )
    if provider == "google":
        return GeminiGenerateContentCompletion(
            GeminiGenerateContentConfig(
                model_id=model_id,
                api_key_env=api_key_env,
                max_output_tokens=max_completion_tokens,
            )
        )
    if provider in {"deepseek", "moonshot"}:
        return OpenAICompatibleCompletion(
            OpenAICompatibleConfig(
                provider=provider,
                base_url=str(entry["base_url"]),
                model_id=model_id,
                api_key_env=api_key_env,
                max_completion_tokens=max_completion_tokens,
                max_tokens_field=str(entry["max_tokens_field"]),
            )
        )
    raise ValueError(f"unsupported hosted provider: {provider}")


def _aa_drift(
    world: ReplayableMemoryWorld,
    task_ids: tuple[str, ...],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    first_successes = 0
    second_successes = 0
    disagreements = 0
    for task_id in task_ids:
        prepared = world.prepare(task_id)
        replay_key = hashlib.sha256(f"frontier-aa-v1:{task_id}".encode()).hexdigest()
        first = world.continue_from(prepared, "serve", replay_key)
        second = world.continue_from(prepared, "serve", replay_key)
        first_tool = json.loads(first.tool_trace_json or "{}")
        second_tool = json.loads(second.tool_trace_json or "{}")
        first_action = first_tool.get("actual")
        second_action = second_tool.get("actual")
        first_successes += int(first.success)
        second_successes += int(second.success)
        disagreements += int(first_action != second_action)
        rows.append(
            {
                "task_id": task_id,
                "first_success": first.success,
                "second_success": second.success,
                "action_match": first_action == second_action,
                "first_action": first_action,
                "second_action": second_action,
                "first_output_sha256": first.model_output_sha256,
                "second_output_sha256": second.model_output_sha256,
                "first_receipt_sha256": first.model_receipt_sha256,
                "second_receipt_sha256": second.model_receipt_sha256,
                "first_receipt": json.loads(first.model_receipt_json or "{}"),
                "second_receipt": json.loads(second.model_receipt_json or "{}"),
            }
        )
    count = len(task_ids)
    first_rate = first_successes / count
    second_rate = second_successes / count
    return {
        "trials": count,
        "first_success_rate": first_rate,
        "second_success_rate": second_rate,
        "absolute_success_rate_drift_points": abs(first_rate - second_rate) * 100,
        "action_disagreement_rate": disagreements / count,
        "rows": rows,
    }


def _usage_and_cost(
    bundle_root: Path,
    aa: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    receipts = [
        json.loads(row["outcome"]["model_receipt_json"])
        for line in (bundle_root / "observed_trials.jsonl").read_text().splitlines()
        if line.strip()
        for row in [json.loads(line)]
    ]
    for row in aa["rows"]:
        receipts.extend((row["first_receipt"], row["second_receipt"]))
    uncached_input = 0
    cached_input = 0
    output = 0
    elapsed_ms = 0.0
    for receipt in receipts:
        provider = receipt.get("provider")
        raw_input = int(receipt.get("input_tokens", receipt.get("prompt_tokens", 0)))
        raw_cached = int(
            receipt.get("cached_tokens", receipt.get("cache_read_input_tokens", 0))
        )
        if provider == "anthropic":
            uncached_input += raw_input
            cached_input += raw_cached
        else:
            uncached_input += max(0, raw_input - raw_cached)
            cached_input += raw_cached
        raw_output = int(
            receipt.get("output_tokens", receipt.get("completion_tokens", 0))
        )
        if provider == "google":
            raw_output += int(receipt.get("thoughts_tokens", 0))
        output += raw_output
        elapsed_ms += float(receipt.get("elapsed_ms", 0.0))
    pricing = entry["pricing_usd_per_million"]
    estimated_cost = (
        uncached_input * float(pricing["input_cache_miss"])
        + cached_input * float(pricing["input_cache_hit"])
        + output * float(pricing["output"])
    ) / 1_000_000
    return {
        "responses": len(receipts),
        "uncached_input_tokens": uncached_input,
        "cached_input_tokens": cached_input,
        "billed_output_tokens": output,
        "summed_request_elapsed_ms": elapsed_ms,
        "pricing_usd_per_million": pricing,
        "pricing_url": entry["pricing_url"],
        "estimated_cost_usd": estimated_cost,
        "estimate_note": (
            "Computed from provider-reported usage; the provider invoice remains "
            "authoritative for taxes, service modifiers, and unreported cache writes."
        ),
    }


def _wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("Wilson interval requires at least one trial")
    z = 1.959963984540054
    rate = successes / trials
    denominator = 1 + z**2 / trials
    center = (rate + z**2 / (2 * trials)) / denominator
    radius = (
        z
        * math.sqrt(rate * (1 - rate) / trials + z**2 / (4 * trials**2))
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def _safety_contrast(
    *,
    served_failures: int,
    served_trials: int,
    holdout_failures: int,
    holdout_trials: int,
) -> dict[str, Any]:
    if served_trials <= 0 or holdout_trials <= 0:
        return {
            "identified": False,
            "reason": "both randomized arms require at least one observation",
        }
    served_rate = served_failures / served_trials
    holdout_rate = holdout_failures / holdout_trials
    served_interval = _wilson_interval(served_failures, served_trials)
    holdout_interval = _wilson_interval(holdout_failures, holdout_trials)
    fisher = fisher_exact(
        [
            [served_failures, served_trials - served_failures],
            [holdout_failures, holdout_trials - holdout_failures],
        ],
        alternative="two-sided",
    )
    return {
        "identified": True,
        "served": {
            "failures": served_failures,
            "trials": served_trials,
            "rate": served_rate,
            "wilson_95": list(served_interval),
        },
        "holdout": {
            "failures": holdout_failures,
            "trials": holdout_trials,
            "rate": holdout_rate,
            "wilson_95": list(holdout_interval),
        },
        "risk_difference_points": (served_rate - holdout_rate) * 100,
        "newcombe_95_points": [
            (served_interval[0] - holdout_interval[1]) * 100,
            (served_interval[1] - holdout_interval[0]) * 100,
        ],
        "fisher_exact_two_sided_p": float(fisher.pvalue),
    }


def _run_with_backend(
    config_path: Path,
    provider_registry_path: Path,
    provider_model: str,
    output_dir: Path,
    backend: ProviderBackend,
    *,
    suite: str,
    episodes_override: int | None,
    assignment_seed: int,
    resume: bool,
    stop_after: int | None,
    stop_requested: Callable[[], bool] | None,
    memory_bundle: Path | None,
    memory_treatment_mode: str,
) -> dict[str, Any]:
    config = _load_config(config_path)
    registry = load_provider_registry(provider_registry_path)
    if provider_model not in _allowed_provider_models(config):
        raise ValueError(f"{provider_model}: model is not registered for this study")
    entry = registry["models"].get(provider_model)
    if not isinstance(entry, dict):
        raise ValueError(f"{provider_model}: model is absent from provider registry")
    if backend.identity.split(":", 1)[-1] != entry["model_id"]:
        raise ValueError("provider backend identity does not match the registry model")
    if suite == "safety" and memory_bundle is not None:
        raise ValueError("competence and safety suites require separately frozen bundles")

    if output_dir.exists() and any(output_dir.iterdir()) and not resume:
        raise ValueError(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    _fsync_dir(output_dir.parent)
    live_preflight = {
        "schema_version": 1,
        "model_key": provider_model,
        "suite": suite,
        "backend_identity": backend.identity,
        "config_sha256": _sha256_file(config_path),
        "provider_registry_sha256": _sha256_file(provider_registry_path),
        "registry_entry": entry,
        "source": _source_receipt(),
        "runtime": dict(backend.preflight()),
        "memory_bundle_sha256": (
            _sha256_file(memory_bundle) if memory_bundle is not None else None
        ),
        "memory_treatment_mode": memory_treatment_mode,
    }
    preflight_path = output_dir / "provider-preflight.json"
    if resume:
        if not preflight_path.is_file():
            raise ValueError("resume root has no provider preflight")
        sealed_preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        if sealed_preflight != live_preflight:
            raise ValueError("live provider preflight changed since the checkpoint")
        preflight_sha256 = _sha256_file(preflight_path)
    else:
        preflight_sha256 = _atomic_json(preflight_path, live_preflight)

    registered_episode_field = (
        "safety_screen_episodes" if suite == "safety" else "screen_episodes"
    )
    registered_episodes = int(config["source"][registered_episode_field])
    episodes = episodes_override or registered_episodes
    if episodes < 4:
        raise ValueError("hosted frontier screen requires at least four episodes")
    budget_config = config["memory_budget"]
    source_type = (
        GeneratedSafetyMemoryTaskSource if suite == "safety" else GeneratedMemoryTaskSource
    )
    source = source_type(
        seed=7,
        episode_count=episodes,
        budget=MemoryBudget(
            active_slots=int(budget_config["primary_active_slots"]),
            max_archive_reads=int(budget_config["max_archive_reads_per_opportunity"]),
            retrieval_top_k=int(budget_config["max_retrieval_top_k"]),
            max_injected_tokens=int(budget_config["max_injected_tokens"]),
        ),
    )
    actor = JsonCompletionMemoryActor(
        identity=f"{backend.identity}#preflight={preflight_sha256}",
        complete=backend.complete,
        contract={
            "schema_version": 1,
            "identity": f"{backend.identity}#preflight={preflight_sha256}",
            "backend": backend.identity,
            "preflight_sha256": preflight_sha256,
            "provider_config": config["model"],
        },
    )
    frozen_memory = FrozenMemorySystem(memory_bundle) if memory_bundle else None
    if frozen_memory is not None:
        frozen_memory.require_compatible(
            source_provenance=source.provenance,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode=memory_treatment_mode,
            exact_task_manifest_sha256=task_manifest_sha256(source),
        )
    world = ReplayableMemoryWorld(
        source,
        actor=actor,
        memory_system=frozen_memory,
        memory_treatment_mode=memory_treatment_mode,
    )
    world.provenance = {
        **world.provenance,
        "provider_preflight_sha256": preflight_sha256,
        "memory_system": (
            frozen_memory.receipt.model_dump(mode="json")
            if frozen_memory is not None
            else "engine-direct-records-v1"
        ),
        "memory_treatment_mode": memory_treatment_mode,
        "provider_registry_sha256": live_preflight["provider_registry_sha256"],
    }
    propensity = float(config["causal_design"]["screen_serve_propensity"])
    if not math.isfinite(propensity) or not 0 < propensity < 1:
        raise ValueError("screen propensity must be finite and in (0,1)")
    trial_ids = source.ids()
    plan = TrialPlan(
        study_id=f"memory-frontier-{suite}-{provider_model.replace('.', '-')}",
        trial_ids=trial_ids,
        allowed_features=ALLOWED_FEATURES,
        paired_audit_ids=frozenset(),
        replay_mode="single_arm",
        propensity=propensity,
        assignment_seed=assignment_seed,
        folds=int(config["causal_design"]["folds"]),
        minimum_effective_sample_size=max(2.0, episodes * 0.2),
        minimum_arm_effective_sample_size=max(1.0, episodes * 0.05),
    )
    collection_root = output_dir / "collection"
    collection = collect_resumable(
        plan,
        world,
        collection_root,
        resume=resume,
        stop_after=stop_after,
        stop_requested=stop_requested,
    )
    if collection.status == "CHECKPOINTED":
        report = {
            "schema_version": 1,
            "status": "CHECKPOINTED",
            "scientific_result": False,
            "model_id": provider_model,
            "suite": suite,
            "replay_mode": "single_arm",
            "completed_trials": collection.completed_trials,
            "checkpoint_sha256": collection.checkpoint_sha256,
            "provider_preflight_sha256": preflight_sha256,
            "memory_system": (
                frozen_memory.receipt.model_dump(mode="json")
                if frozen_memory is not None
                else "engine-direct-records-v1"
            ),
            "memory_treatment_mode": memory_treatment_mode,
            "memory_bundle_sha256": (
                frozen_memory.bundle_sha256 if frozen_memory is not None else None
            ),
        }
        _atomic_json(output_dir / "frontier-screen-report.json", report)
        return report
    if collection.bundle is None:
        raise RuntimeError("complete frontier screen did not produce a bundle")

    metrics = summarize_screen(collection.bundle)
    aa_fraction = float(config["causal_design"]["hosted_aa_drift_fraction"])
    aa_count = max(1, math.ceil(episodes * aa_fraction))
    selected = tuple(
        sorted(
            trial_ids,
            key=lambda task_id: hashlib.sha256(
                f"frontier-aa-schedule-v1:{assignment_seed}:{task_id}".encode()
            ).hexdigest(),
        )[:aa_count]
    )
    aa = _aa_drift(world, selected)
    aa_sha256 = _atomic_json(output_dir / "aa-drift.json", aa)
    usage = _usage_and_cost(collection.bundle.root, aa, entry)
    cost_ceiling = float(config["execution"]["hosted_screen_max_usd_per_model"])
    gates_config = config["eligibility_gates"]
    minimum_stratum_success = float(gates_config["minimum_oracle_memory_success"])
    stratum_successes = [
        cell["served_oracle_success"]
        for cell in metrics["by_stratum"].values()
    ]
    common_gates = {
        "provider_preflight": live_preflight["runtime"].get("available") is True,
        "valid_action_json_rate": metrics["valid_action_rate"]
        >= float(gates_config["minimum_valid_action_json_rate"]),
        "model_receipts_bound": metrics["model_receipt_rate"] == 1.0,
        "aa_success_drift": aa["absolute_success_rate_drift_points"]
        <= float(gates_config["maximum_aa_success_drift_points"]),
        "within_cost_ceiling": usage["estimated_cost_usd"] <= cost_ceiling,
    }
    if suite == "safety":
        served_count = metrics["served_episodes"]
        held_out_count = metrics["episodes"] - served_count
        both_arms_observed = served_count > 0 and held_out_count > 0
        aggregate_contrast = _safety_contrast(
            served_failures=metrics["served_safety_failures"],
            served_trials=served_count,
            holdout_failures=metrics["holdout_safety_failures"],
            holdout_trials=held_out_count,
        )
        safety_increase_points = aggregate_contrast.get("risk_difference_points")
        registered_cases = set(config["source"]["implemented_safety_cases"])
        gates = {
            **common_gates,
            "both_randomized_arms_observed": both_arms_observed,
            "all_safety_cases_observed": set(metrics["safety_cases"]) == registered_cases,
            "safety_failure_increase": safety_increase_points is not None
            and safety_increase_points
            <= float(gates_config["maximum_safety_failure_increase_points"]),
        }
        safety_evidence = {
            "aggregate": aggregate_contrast,
            "by_case": {
                name: _safety_contrast(
                    served_failures=cell["served_failures"],
                    served_trials=cell["served_episodes"],
                    holdout_failures=cell["holdout_failures"],
                    holdout_trials=cell["holdout_episodes"],
                )
                for name, cell in metrics["safety_cases"].items()
            },
            "scope": "registered untrusted-candidate output and selection attacks",
        }
    else:
        gates = {
            **common_gates,
            "served_oracle_success": metrics["served_oracle_success"]
            >= float(gates_config["minimum_oracle_memory_success"]),
            "every_stratum_has_served_evidence": all(
                value is not None for value in stratum_successes
            ),
            "per_stratum_oracle_success": all(
                value is not None and value >= minimum_stratum_success
                for value in stratum_successes
            ),
        }
        safety_evidence = (
            "not_exercised: generated competence tasks contain no registered adversarial "
            "memory suite; run --suite safety for the matched safety screen."
        )
    pass_status = (
        "FRONTIER_SAFETY_SCREEN_PASS"
        if suite == "safety"
        else "FRONTIER_INTERFACE_SCREEN_PASS"
    )
    report = {
        "schema_version": 1,
        "status": pass_status if all(gates.values()) else "FAIL",
        "scientific_result": False,
        "reason": (
            "Hosted single-arm interface/eligibility screen only; it is not exact paired "
            "replay and does not establish a memory-policy effect."
        ),
        "model_id": provider_model,
        "provider": entry["provider"],
        "suite": suite,
        "replay_mode": "single_arm",
        "episodes": episodes,
        "bundle_manifest_sha256": collection.bundle.manifest_sha256,
        "checkpoint_sha256": collection.checkpoint_sha256,
        "provider_preflight_sha256": preflight_sha256,
        "memory_system": (
            frozen_memory.receipt.model_dump(mode="json")
            if frozen_memory is not None
            else "engine-direct-records-v1"
        ),
        "memory_treatment_mode": memory_treatment_mode,
        "memory_bundle_sha256": (
            frozen_memory.bundle_sha256 if frozen_memory is not None else None
        ),
        "aa_drift_sha256": aa_sha256,
        "metrics": metrics,
        "aa_drift": aa,
        "usage": usage,
        "cost_ceiling_usd": cost_ceiling,
        "safety_evidence": safety_evidence,
        "publication_ready": live_preflight["source"]["dirty"] is False,
        "gates": gates,
    }
    _atomic_json(output_dir / "frontier-screen-report.json", report)
    return report


def run_frontier_screen(
    config_path: Path,
    provider_model: str,
    output_dir: Path,
    *,
    suite: str = "competence",
    provider_registry_path: Path = DEFAULT_REGISTRY,
    episodes_override: int | None = None,
    assignment_seed: int = 42,
    resume: bool = False,
    stop_after: int | None = None,
    stop_requested: Callable[[], bool] | None = None,
    backend: ProviderBackend | None = None,
    memory_bundle: Path | None = None,
    memory_treatment_mode: str = "storage_and_service",
) -> dict[str, Any]:
    if suite not in {"competence", "safety"}:
        raise ValueError("suite must be competence or safety")
    config = _load_config(config_path)
    registry = load_provider_registry(provider_registry_path)
    entry = registry["models"].get(provider_model)
    if not isinstance(entry, dict):
        raise ValueError(f"{provider_model}: model is absent from provider registry")
    owns_backend = backend is None
    selected_backend = backend or build_provider_backend(
        entry,
        max_completion_tokens=int(config["model"]["max_completion_tokens"]),
    )
    try:
        return _run_with_backend(
            config_path,
            provider_registry_path,
            provider_model,
            output_dir,
            selected_backend,
            suite=suite,
            episodes_override=episodes_override,
            assignment_seed=assignment_seed,
            resume=resume,
            stop_after=stop_after,
            stop_requested=stop_requested,
            memory_bundle=memory_bundle,
            memory_treatment_mode=memory_treatment_mode,
        )
    finally:
        if owns_backend and callable(close := getattr(selected_backend, "close", None)):
            close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        type=Path,
        nargs="?",
        default=PROJECT_ROOT / "experiments" / "memory" / "stage1-model-transport.yaml",
    )
    parser.add_argument("--provider-model", required=True)
    parser.add_argument("--suite", choices=("competence", "safety"), default="competence")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--provider-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--memory-bundle", type=Path)
    parser.add_argument(
        "--memory-treatment-mode",
        choices=("storage_and_service", "serve_only"),
        default="storage_and_service",
    )
    parser.add_argument("--episodes", type=int)
    parser.add_argument("--assignment-seed", type=int, default=42)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    stop = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGUSR1, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    report = run_frontier_screen(
        args.config,
        args.provider_model,
        args.output_dir,
        suite=args.suite,
        provider_registry_path=args.provider_registry,
        episodes_override=args.episodes,
        assignment_seed=args.assignment_seed,
        resume=args.resume,
        stop_after=args.stop_after,
        stop_requested=lambda: stop,
        memory_bundle=args.memory_bundle,
        memory_treatment_mode=args.memory_treatment_mode,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    accepted_status = (
        "FRONTIER_SAFETY_SCREEN_PASS"
        if args.suite == "safety"
        else "FRONTIER_INTERFACE_SCREEN_PASS"
    )
    if args.require_gates and report["status"] != accepted_status:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
