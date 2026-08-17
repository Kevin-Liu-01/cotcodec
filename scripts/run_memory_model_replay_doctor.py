#!/usr/bin/env python3
"""Run a bounded strict-determinism replay falsifier on a pinned open model."""

from __future__ import annotations

import argparse
import gc
import json
import os
import random
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    MemoryBudget,
    ReplayableMemoryWorld,
    TransformersMemoryActor,
    task_manifest_sha256,
)
from scripts.fetch_open_model import (  # noqa: E402
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
    load_registry,
    verify_receipt,
)
from scripts.run_memory_trials import atomic_json, sha256_file  # noqa: E402

PROGRESS_SCHEMA_VERSION = 1
REPLAY_VISIBILITIES = ("serve", "holdout")


def _case_key(
    seed: int,
    reload_index: int,
    task_id: str,
    visibility: str,
) -> tuple[int, int, str, str]:
    return seed, reload_index, task_id, visibility


def _expected_case_keys(
    *,
    seeds: tuple[int, ...],
    cold_reloads: int,
    task_ids: tuple[str, ...],
) -> tuple[tuple[int, int, str, str], ...]:
    return tuple(
        _case_key(seed, reload_index, task_id, visibility)
        for seed in seeds
        for reload_index in range(cold_reloads)
        for task_id in task_ids
        for visibility in REPLAY_VISIBILITIES
    )


def _row_key(row: dict[str, Any]) -> tuple[int, int, str, str]:
    return _case_key(
        int(row["seed"]),
        int(row["reload"]),
        str(row["task_id"]),
        str(row["visibility"]),
    )


def _progress_payload(
    contract: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    status: str = "IN_PROGRESS",
) -> dict[str, Any]:
    return {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "status": status,
        "contract": contract,
        "completed_cases": len(rows),
        "rows": rows,
    }


def _load_progress(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    expected_keys: tuple[tuple[int, int, str, str], ...],
) -> list[dict[str, Any]]:
    checkpoint_path = output_dir / "checkpoint.json"
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return []
    existing = tuple(output_dir.iterdir())
    if not existing:
        return []
    if not checkpoint_path.is_file():
        raise ValueError(
            "nonempty replay-doctor output lacks a resumable checkpoint"
        )
    if (output_dir / "report.json").exists():
        raise ValueError("replay-doctor output is already finalized")
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != PROGRESS_SCHEMA_VERSION
        or payload.get("contract") != contract
    ):
        raise ValueError("replay-doctor checkpoint contract mismatch")
    checkpoint_status = payload.get("status")
    if checkpoint_status not in {"IN_PROGRESS", "COMPLETE"}:
        raise ValueError("replay-doctor checkpoint status is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or not all(
        isinstance(row, dict) for row in raw_rows
    ):
        raise ValueError("replay-doctor checkpoint rows are malformed")
    rows = [dict(row) for row in raw_rows]
    keys = tuple(_row_key(row) for row in rows)
    if keys != expected_keys[: len(keys)]:
        raise ValueError("replay-doctor checkpoint is not a contiguous plan prefix")
    if payload.get("completed_cases") != len(rows):
        raise ValueError("replay-doctor checkpoint count mismatch")
    if checkpoint_status == "COMPLETE" and len(rows) != len(expected_keys):
        raise ValueError("complete replay-doctor checkpoint is truncated")
    return rows


def _write_progress(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    rows: list[dict[str, Any]],
    status: str = "IN_PROGRESS",
) -> None:
    atomic_json(
        output_dir / "checkpoint.json",
        _progress_payload(contract, rows, status=status),
    )


def _acknowledge_checkpoint(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    _write_progress(output_dir, contract=contract, rows=rows)
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    if marker:
        atomic_json(
            Path(marker),
            {
                "schema_version": 1,
                "status": "CHECKPOINT_READY",
                "checkpoint": "replay-doctor/checkpoint.json",
                "completed_cases": len(rows),
                "total_cases": len(
                    _expected_case_keys(
                        seeds=tuple(contract["seeds"]),
                        cold_reloads=int(contract["cold_reloads"]),
                        task_ids=tuple(contract["task_ids"]),
                    )
                ),
            },
        )


def _task_id(value: str) -> str:
    if value.startswith("memory-"):
        return value
    index = int(value)
    if index < 0:
        raise ValueError("task indices must be nonnegative")
    return f"memory-{index:06d}"


def run_doctor(
    *,
    config_path: Path,
    output_dir: Path,
    model_id: str,
    registry_path: Path,
    model_root: Path,
    receipt_root: Path,
    task_ids: tuple[str, ...],
    repetitions: int,
    cold_reloads: int,
    seeds: tuple[int, ...],
    memory_bundle: Path | None,
    stop_requested: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    if repetitions < 2 or cold_reloads < 2:
        raise ValueError("replay doctor requires at least two repeats and two cold loads")
    if len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise ValueError("replay doctor requires at least three distinct seeds")
    should_stop = stop_requested or (lambda: False)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if not isinstance(entry, dict) or entry.get("backend") != "huggingface":
        raise ValueError(f"{model_id}: replay doctor requires a pinned Hugging Face model")
    if entry["trust_remote_code"] or not entry["publication_eligible"]:
        raise ValueError(f"{model_id}: unreviewed or ineligible checkpoint")
    receipt = verify_receipt(model_id, entry, model_root, receipt_root)
    if receipt.get("mode") != "full":
        raise ValueError("replay doctor requires a full model artifact receipt")
    budget_config = config["memory_budget"]
    budget = MemoryBudget(
        active_slots=int(budget_config["primary_active_slots"]),
        max_archive_reads=int(budget_config["max_archive_reads_per_opportunity"]),
        retrieval_top_k=int(budget_config["max_retrieval_top_k"]),
        max_injected_tokens=int(budget_config["max_injected_tokens"]),
    )
    episode_count = max(200, max(int(item.removeprefix("memory-")) for item in task_ids) + 1)
    source = GeneratedMemoryTaskSource(
        seed=7,
        episode_count=episode_count,
        budget=budget,
    )
    frozen = FrozenMemorySystem(memory_bundle) if memory_bundle is not None else None
    if frozen is not None:
        frozen.require_compatible(
            source_provenance=source.provenance,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode="storage_and_service",
            exact_task_manifest_sha256=task_manifest_sha256(source),
        )
    roster = {
        item["model_id"]: item
        for item in config["model"]["open_roster"]
        if isinstance(item, dict) and isinstance(item.get("model_id"), str)
    }
    if model_id not in roster:
        raise ValueError(f"{model_id}: absent from the registered model-transport roster")

    contract = {
        "schema_version": 1,
        "config_sha256": sha256_file(config_path),
        "model_id": model_id,
        "revision": entry["revision"],
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "task_manifest_sha256": task_manifest_sha256(source),
        "memory_bundle_sha256": frozen.bundle_sha256 if frozen is not None else None,
        "task_ids": list(task_ids),
        "seeds": list(seeds),
        "repetitions": repetitions,
        "cold_reloads": cold_reloads,
        "visibilities": list(REPLAY_VISIBILITIES),
        "deterministic": True,
        "attention_implementation": "eager",
    }
    expected_keys = _expected_case_keys(
        seeds=seeds,
        cold_reloads=cold_reloads,
        task_ids=task_ids,
    )
    rows = _load_progress(
        output_dir,
        contract=contract,
        expected_keys=expected_keys,
    )
    completed_keys = {_row_key(row) for row in rows}
    signatures_by_case: dict[str, tuple[str | None, str | None]] = {}
    failures: list[dict[str, Any]] = []
    for row in rows:
        output_sha256s = row.get("output_sha256s")
        tool_trace_sha256s = row.get("tool_trace_sha256s")
        if (
            not isinstance(output_sha256s, list)
            or len(output_sha256s) != repetitions
            or not isinstance(tool_trace_sha256s, list)
            or len(tool_trace_sha256s) != repetitions
        ):
            raise ValueError("replay-doctor checkpoint signatures are malformed")
        case_id = f"{row['task_id']}:{row['visibility']}"
        signature = (output_sha256s[0], tool_trace_sha256s[0])
        expected_cross_load = (
            case_id not in signatures_by_case
            or signatures_by_case[case_id] == signature
        )
        if row.get("cross_load_seed_exact") is not expected_cross_load:
            raise ValueError("replay-doctor checkpoint cross-load result mismatch")
        signatures_by_case.setdefault(case_id, signature)
        if not all(
            bool(row.get(field))
            for field in (
                "pre_model_equal",
                "token_exact",
                "action_exact",
                "cross_load_seed_exact",
            )
        ):
            failures.append(row)
    if should_stop():
        _acknowledge_checkpoint(
            output_dir,
            contract=contract,
            rows=rows,
        )
        return {
            "schema_version": 1,
            "status": "CHECKPOINTED",
            "scientific_result": False,
            "completed_cases": len(rows),
            "total_cases": len(expected_keys),
        }

    workspace = os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    if workspace != ":4096:8":
        raise ValueError("replay doctor requires CUBLAS_WORKSPACE_CONFIG=:4096:8")
    for seed in seeds:
        for reload_index in range(cold_reloads):
            block_keys = {
                _case_key(seed, reload_index, task_id, visibility)
                for task_id in task_ids
                for visibility in REPLAY_VISIBILITIES
            }
            if block_keys <= completed_keys:
                continue
            random.seed(seed)
            import torch

            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            actor = TransformersMemoryActor.from_snapshot(
                snapshot=model_root / model_id,
                model_id=model_id,
                revision=entry["revision"],
                artifact_root_sha256=receipt["artifact_root_sha256"],
                max_new_tokens=int(config["model"]["max_completion_tokens"]),
                dtype=str(config["model"].get("dtype", "bfloat16")),
                use_chat_template="chat_template.jinja" in entry["required_files"],
                deterministic=True,
                attention_implementation="eager",
            )
            world = ReplayableMemoryWorld(source, actor=actor, memory_system=frozen)
            reload_rows: list[dict[str, Any]] = []
            for task_id in task_ids:
                prepared = world.prepare(task_id)
                for visibility in REPLAY_VISIBILITIES:
                    current_key = _case_key(
                        seed,
                        reload_index,
                        task_id,
                        visibility,
                    )
                    if current_key in completed_keys:
                        reload_rows.append(
                            next(row for row in rows if _row_key(row) == current_key)
                        )
                        continue
                    replay_key = (
                        f"strict-replay-{task_id}-{visibility}"
                        .encode()
                        .hex()[:64]
                        .ljust(64, "0")
                    )
                    outcomes = [
                        world.continue_from(prepared, visibility, replay_key)
                        for _ in range(repetitions)
                    ]
                    first = outcomes[0]
                    pre_model_equal = all(
                        outcome.prompt_sha256 == first.prompt_sha256
                        and outcome.memory_frame_sha256 == first.memory_frame_sha256
                        and outcome.restored_snapshot_sha256
                        == first.restored_snapshot_sha256
                        for outcome in outcomes[1:]
                    )
                    token_exact = all(
                        outcome.model_output_sha256 == first.model_output_sha256
                        for outcome in outcomes[1:]
                    )
                    action_exact = all(
                        outcome.tool_trace_sha256 == first.tool_trace_sha256
                        for outcome in outcomes[1:]
                    )
                    case_id = f"{task_id}:{visibility}"
                    signature = (first.model_output_sha256, first.tool_trace_sha256)
                    cross_load_seed_exact = (
                        case_id not in signatures_by_case
                        or signatures_by_case[case_id] == signature
                    )
                    signatures_by_case.setdefault(case_id, signature)
                    row = {
                        "seed": seed,
                        "reload": reload_index,
                        "task_id": task_id,
                        "visibility": visibility,
                        "repetitions": repetitions,
                        "pre_model_equal": pre_model_equal,
                        "token_exact": token_exact,
                        "action_exact": action_exact,
                        "cross_load_seed_exact": cross_load_seed_exact,
                        "prompt_sha256": first.prompt_sha256,
                        "memory_frame_sha256": first.memory_frame_sha256,
                        "output_sha256s": [
                            item.model_output_sha256 for item in outcomes
                        ],
                        "tool_trace_sha256s": [
                            item.tool_trace_sha256 for item in outcomes
                        ],
                        "model_receipts": [
                            json.loads(item.model_receipt_json or "{}")
                            for item in outcomes
                        ],
                    }
                    reload_rows.append(row)
                    rows.append(row)
                    completed_keys.add(current_key)
                    if not all(
                        (
                            pre_model_equal,
                            token_exact,
                            action_exact,
                            cross_load_seed_exact,
                        )
                    ):
                        failures.append(row)
                    _write_progress(
                        output_dir,
                        contract=contract,
                        rows=rows,
                    )
                    if should_stop():
                        _acknowledge_checkpoint(
                            output_dir,
                            contract=contract,
                            rows=rows,
                        )
                        return {
                            "schema_version": 1,
                            "status": "CHECKPOINTED",
                            "scientific_result": False,
                            "completed_cases": len(rows),
                            "total_cases": len(expected_keys),
                        }
            atomic_json(
                output_dir / f"seed-{seed}-reload-{reload_index}.json",
                {
                    "schema_version": 1,
                    "seed": seed,
                    "reload": reload_index,
                    "rows": reload_rows,
                },
            )
            del world, actor
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    report = {
        "schema_version": 1,
        "status": "STRICT_REPLAY_PASS" if not failures else "FAIL",
        "scientific_result": False,
        "reason": "Kernel/replay transport falsifier only; no memory-policy result.",
        "model_id": model_id,
        "revision": entry["revision"],
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "memory_bundle_sha256": frozen.bundle_sha256 if frozen is not None else None,
        "task_ids": list(task_ids),
        "seeds": list(seeds),
        "repetitions": repetitions,
        "cold_reloads": cold_reloads,
        "rows": rows,
        "failures": failures,
    }
    atomic_json(output_dir / "report.json", report)
    _write_progress(
        output_dir,
        contract=contract,
        rows=rows,
        status="COMPLETE",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        type=Path,
        default=Path("experiments/memory/stage1-model-transport.yaml"),
        nargs="?",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--cold-reloads", type=int, default=2)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--memory-bundle", type=Path)
    args = parser.parse_args()
    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGUSR1, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    report = run_doctor(
        config_path=args.config,
        output_dir=args.output_dir,
        model_id=args.model_id,
        registry_path=args.registry,
        model_root=args.model_root,
        receipt_root=args.receipt_root,
        task_ids=tuple(
            _task_id(item) for item in (args.task_id or ["0", "4", "106", "180"])
        ),
        repetitions=args.repetitions,
        cold_reloads=args.cold_reloads,
        seeds=tuple(args.seeds),
        memory_bundle=args.memory_bundle,
        stop_requested=lambda: stop,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "CHECKPOINTED":
        return 75
    return 0 if report["status"] == "STRICT_REPLAY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
