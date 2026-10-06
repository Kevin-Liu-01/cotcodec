#!/usr/bin/env python3
"""Validate source contracts and, when present, pinned public benchmark data."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
    LONGMEMEVAL_ORACLE_FILENAME,
    LONGMEMEVAL_ORACLE_SHA256,
    LONGMEMEVAL_ORACLE_SIZE,
    LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    EventKind,
    LongMemEvalTaskSource,
    MemoryBudget,
    MemoryEvent,
    MemoryOracle,
    MemoryStratum,
    MemoryTask,
    NoMemorySystem,
    ReplayableMemoryWorld,
    build_memory_system_request,
    run_memory_system,
    task_manifest_sha256,
)
from harness.memory_trials.models import ModelAction, action_success  # noqa: E402
from harness.memory_trials.schema import seal_task  # noqa: E402

DEFAULT_LONGMEMEVAL_PATH = (
    PROJECT_ROOT
    / "data"
    / "benchmarks"
    / "longmemeval"
    / LONGMEMEVAL_DATASET_REVISION
    / LONGMEMEVAL_ORACLE_FILENAME
)


class FixtureMemoryTaskSource:
    """Two source-shaped fixtures; no benchmark content is embedded here."""

    identity = "mem2act-shaped-fixtures-v1"

    def __init__(self) -> None:
        self.budget = MemoryBudget()
        self.provenance: Mapping[str, Any] = {
            "source": self.identity,
            "license": "synthetic-repository-fixture",
            "public_benchmark_ingested": False,
        }
        self._tasks = {
            "fixture-tool-multifield": self._tool_task(),
            "fixture-update-conflict": self._update_task(),
        }

    def ids(self) -> tuple[str, ...]:
        return tuple(self._tasks)

    def load(self, task_id: str) -> MemoryTask:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"unknown fixture task: {task_id}") from exc

    def _tool_task(self) -> MemoryTask:
        events = (
            MemoryEvent(
                event_id="tool-baseline",
                step=0,
                kind=EventKind.WRITE,
                entity_id="package-17",
                key="destination",
                value="east-hub",
            ),
            MemoryEvent(
                event_id="tool-candidate",
                step=1,
                kind=EventKind.WRITE,
                entity_id="package-17",
                key="destination",
                value="west-hub",
                candidate=True,
            ),
            MemoryEvent(
                event_id="tool-observation",
                step=2,
                kind=EventKind.OBSERVE,
                entity_id="package-17",
                key="status",
                value="ready",
            ),
            MemoryEvent(
                event_id="tool-query",
                step=3,
                kind=EventKind.QUERY,
                entity_id="package-17",
                key="destination",
            ),
        )
        return seal_task(
            {
                "schema_version": "1.0",
                "source_schema_version": "mem2act-shaped-fixture-v1",
                "task_id": "fixture-tool-multifield",
                "group_id": "fixture-tool-family",
                "session_id": "fixture-session-tool",
                "stratum": MemoryStratum.PROACTIVE_TOOL,
                "events": events,
                "candidate_id": "tool-candidate",
                "write_step": 1,
                "eligibility_step": 2,
                "total_steps": len(events),
                "query": "Route package-17 using its saved destination.",
                "oracle": MemoryOracle(
                    mode="tool",
                    lookup_key="destination",
                    expected_value="west-hub",
                    tool_name="route_package",
                    tool_arguments={
                        "item_id": "package-17",
                        "destination": "west-hub",
                        "priority": 2,
                    },
                    tool_input_schema={
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "destination": {"type": "string"},
                            "priority": {"type": "integer"},
                        },
                        "required": ["item_id", "destination", "priority"],
                        "additionalProperties": False,
                    },
                ),
                "budget": self.budget,
                "suffix_variant_id": "primary",
            }
        )

    def _update_task(self) -> MemoryTask:
        events = (
            MemoryEvent(
                event_id="update-baseline",
                step=0,
                kind=EventKind.WRITE,
                entity_id="account-4",
                key="region",
                value="north",
            ),
            MemoryEvent(
                event_id="update-candidate",
                step=1,
                kind=EventKind.UPDATE,
                entity_id="account-4",
                key="region",
                value="south",
                contradiction_count=1,
                candidate=True,
            ),
            MemoryEvent(
                event_id="update-observation",
                step=2,
                kind=EventKind.OBSERVE,
                entity_id="account-4",
                key="status",
                value="confirmed",
            ),
            MemoryEvent(
                event_id="update-query",
                step=3,
                kind=EventKind.QUERY,
                entity_id="account-4",
                key="region",
            ),
        )
        return seal_task(
            {
                "schema_version": "1.0",
                "source_schema_version": "mem2act-shaped-fixture-v1",
                "task_id": "fixture-update-conflict",
                "group_id": "fixture-update-family",
                "session_id": "fixture-session-update",
                "stratum": MemoryStratum.ACTIVE_CORE,
                "events": events,
                "candidate_id": "update-candidate",
                "write_step": 1,
                "eligibility_step": 2,
                "total_steps": len(events),
                "query": "What is account-4's current region?",
                "oracle": MemoryOracle(
                    mode="answer",
                    lookup_key="region",
                    expected_value="south",
                ),
                "budget": self.budget,
                "suffix_variant_id": "primary",
            }
        )


def _nested_field_names(value: Any) -> set[str]:
    if isinstance(value, dict):
        fields = set(value)
        for item in value.values():
            fields.update(_nested_field_names(item))
        return fields
    if isinstance(value, list):
        fields = set()
        for item in value:
            fields.update(_nested_field_names(item))
        return fields
    return set()


def validate_public_longmemeval(
    path: Path,
    *,
    expected_task_count: int = 500,
    expected_sha256: str = LONGMEMEVAL_ORACLE_SHA256,
    expected_size: int = LONGMEMEVAL_ORACLE_SIZE,
    dataset_revision: str = LONGMEMEVAL_DATASET_REVISION,
    artifact_role: str = LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
) -> dict[str, Any]:
    """Validate the complete pinned public task source without running a model."""

    source = LongMemEvalTaskSource(
        path,
        expected_sha256=expected_sha256,
        expected_size=expected_size,
        dataset_revision=dataset_revision,
        artifact_role=artifact_role,
    )
    tasks = tuple(source.load(task_id) for task_id in source.ids())
    if len(tasks) != expected_task_count:
        raise RuntimeError(
            f"LongMemEval task count changed: {len(tasks)} != {expected_task_count}"
        )
    if any(sum(event.candidate for event in task.events) != 1 for task in tasks):
        raise RuntimeError("LongMemEval must have exactly one candidate per task")
    if any(task.write_step >= task.eligibility_step for task in tasks):
        raise RuntimeError("LongMemEval candidate must precede the query")
    forbidden_wire_fields = {
        "answer",
        "answer_session_ids",
        "candidate",
        "has_answer",
        "oracle",
    }
    for task in tasks:
        request, _expected = build_memory_system_request(
            task,
            visibility="serve",
            treatment_mode="storage_and_service",
        )
        request_fields = _nested_field_names(request.model_dump(mode="json"))
        if leaked := forbidden_wire_fields & request_fields:
            raise RuntimeError(
                f"{task.task_id}: public memory request leaked fields {sorted(leaked)}"
            )
    strata = Counter(task.stratum.value for task in tasks)
    groups = Counter(task.group_id for task in tasks)
    return {
        "source": source.identity,
        "dataset_revision": source.provenance["dataset_revision"],
        "dataset_sha256": source.provenance["dataset_sha256"],
        "dataset_size": source.provenance["dataset_size"],
        "dataset_license": source.provenance["dataset_license"],
        "adapter_version": source.provenance["adapter_version"],
        "artifact_role": source.provenance["artifact_role"],
        "retrieval_evaluation_capable": source.provenance[
            "retrieval_evaluation_capable"
        ],
        "candidate_policy": source.provenance["candidate_policy"],
        "candidate_forbidden_inputs": source.provenance[
            "candidate_forbidden_inputs"
        ],
        "task_count": len(tasks),
        "group_count": len(groups),
        "duplicate_group_count": sum(count > 1 for count in groups.values()),
        "strata": dict(sorted(strata.items())),
        "task_manifest_sha256": task_manifest_sha256(source),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--longmemeval-path",
        type=Path,
        default=DEFAULT_LONGMEMEVAL_PATH,
    )
    parser.add_argument(
        "--longmemeval-role",
        choices=(
            LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
            LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
        ),
        default=LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
    )
    parser.add_argument("--require-public-benchmark", action="store_true")
    args = parser.parse_args()

    source = FixtureMemoryTaskSource()
    world = ReplayableMemoryWorld(source)
    receipts: list[dict[str, Any]] = []
    for task_id in source.ids():
        prepared = world.prepare(task_id)
        permuted = world.prepare_suffix_permutation(task_id)
        if prepared.prefix_digest != permuted.prefix_digest:
            raise RuntimeError("engine-owned suffix audit changed the prefix")
        if prepared.features != permuted.features:
            raise RuntimeError("engine-owned suffix audit changed write-time features")
        if prepared.snapshot_sha256 == permuted.snapshot_sha256:
            raise RuntimeError("engine-owned suffix audit did not change the snapshot")
        replay_key = "a" * 64
        served = world.continue_from(prepared, "serve", replay_key)
        repeated = world.continue_from(prepared, "serve", replay_key)
        holdout = world.continue_from(prepared, "holdout", replay_key)
        if served != repeated:
            raise RuntimeError(f"{task_id}: same-arm replay mismatch")
        if not served.success or holdout.success:
            raise RuntimeError(f"{task_id}: fixture treatment effect is not executable")
        if served.exogenous_trace_sha256 != holdout.exogenous_trace_sha256:
            raise RuntimeError(f"{task_id}: treatment changed the exogenous suffix")
        receipts.append(
            {
                "task_id": task_id,
                "task_sha256": source.load(task_id).task_sha256,
                "prefix_sha256": prepared.prefix_digest,
                "served_trace_sha256": served.trace_sha256,
                "holdout_trace_sha256": holdout.trace_sha256,
            }
        )

    tool_oracle = source.load("fixture-tool-multifield").oracle
    wrong_type = ModelAction(
        mode="tool",
        tool_name="route_package",
        tool_arguments={
            "item_id": "package-17",
            "destination": "west-hub",
            "priority": "2",
        },
    )
    if action_success(wrong_type, tool_oracle):
        raise RuntimeError("typed tool oracle accepted a string in place of an integer")

    no_memory = run_memory_system(
        NoMemorySystem(),
        source.load("fixture-tool-multifield"),
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    if no_memory.evidence or any(
        (
            no_memory.costs.reads,
            no_memory.costs.writes,
            no_memory.costs.injected_tokens_estimate,
        )
    ):
        raise RuntimeError("no-memory floor exposed evidence or charged memory operations")

    public_benchmark = None
    if args.longmemeval_path.is_file():
        public_benchmark = validate_public_longmemeval(
            args.longmemeval_path,
            artifact_role=args.longmemeval_role,
        )
    elif args.require_public_benchmark:
        raise RuntimeError(
            f"required LongMemEval artifact is missing: {args.longmemeval_path}"
        )

    print(
        json.dumps(
            {
                "schema_version": 1,
                "status": "PASS",
                "source": source.identity,
                "public_benchmark_ingested": public_benchmark is not None,
                "public_benchmark": public_benchmark,
                "tasks": receipts,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
