#!/usr/bin/env python3
"""Run the registered deterministic ``memory-lifecycle-v1`` CPU contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.lifecycle import (  # noqa: E402
    LifecycleCommand,
    LifecycleEvent,
    LifecycleQuery,
    LifecycleSystemReceipt,
    LifecycleTraceReceipt,
    MemoryLifecycleError,
    SubprocessLifecyclePort,
    run_lifecycle_plan,
)
from harness.memory_trials.lifecycle_study import (  # noqa: E402
    LIFECYCLE_FAMILIES,
    LifecycleStudyCase,
    compile_lifecycle_matrix,
    compile_restore_plan,
    evaluate_lifecycle_case,
    ordered_root,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.validate_memory_lifecycle_experiment import (  # noqa: E402
    load_and_validate_experiment,
)

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage3-lifecycle-mechanism-screen.yaml"
)
REFERENCE_SIDECAR = PROJECT_ROOT / "scripts" / "run_reference_memory_lifecycle_sidecar.py"
CODE_RECEIPT_PATHS = (
    PROJECT_ROOT / "harness" / "memory_trials" / "__init__.py",
    PROJECT_ROOT / "harness" / "memory_trials" / "schema.py",
    PROJECT_ROOT / "harness" / "memory_trials" / "lifecycle.py",
    PROJECT_ROOT / "harness" / "memory_trials" / "lifecycle_study.py",
    PROJECT_ROOT / "scripts" / "run_reference_memory_lifecycle_sidecar.py",
    PROJECT_ROOT / "scripts" / "run_memory_lifecycle_contract.py",
    PROJECT_ROOT / "scripts" / "validate_memory_lifecycle_experiment.py",
    PROJECT_ROOT / "infra" / "research" / "Dockerfile.lifecycle-cpu",
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "uv.lock",
)
SEALED_ARTIFACT_FILENAMES = (
    "experiment.yaml",
    "plans.jsonl",
    "traces.jsonl",
    "restore-traces.jsonl",
    "case-results.jsonl",
    "checkpoint-audit.json",
    "isolation-purge-audit.json",
    "costs-by-phase.json",
    "report.json",
)
SEALED_OUTPUT_FILENAMES = frozenset((*SEALED_ARTIFACT_FILENAMES, "manifest.json"))
RUNNER_GATE_NAMES = frozenset(
    {
        "exact_total_trace_count",
        "exact_active_slot_cell_counts",
        "exact_family_counts",
        "all_case_gates_pass",
        "all_checkpoint_suffixes_exact",
        "isolation_and_purge_audit_pass",
        "system_receipts_non_publication",
        "no_model_or_gpu_calls",
    }
)


class LifecycleRunError(RuntimeError):
    """Raised when the registered lifecycle run cannot be sealed honestly."""


def _sha256_bytes(encoded: bytes) -> str:
    return hashlib.sha256(encoded).hexdigest()


def _sha256_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise LifecycleRunError(f"evidence input must be a regular file: {path}")
    return _sha256_bytes(path.read_bytes())


def _code_receipt() -> dict[str, dict[str, str | int]]:
    return {
        str(path.relative_to(PROJECT_ROOT)): {
            "sha256": _sha256_path(path),
            "size": path.stat().st_size,
        }
        for path in CODE_RECEIPT_PATHS
    }


def _write_once(path: Path, encoded: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(encoded)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise LifecycleRunError(f"short write while sealing {path.name}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _jsonl_bytes(values: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(value) for value in values) + "\n").encode()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LifecycleRunError(f"duplicate JSON key in sealed evidence: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise LifecycleRunError(f"non-finite JSON constant in sealed evidence: {value}")


def _load_json_bytes(encoded: bytes, *, label: str) -> Any:
    try:
        text = encoded.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleRunError(f"{label} is not strict UTF-8 JSON") from exc


def _load_jsonl_bytes(encoded: bytes, *, label: str) -> list[dict[str, Any]]:
    if not encoded.endswith(b"\n"):
        raise LifecycleRunError(f"{label} must end with one newline")
    lines = encoded.splitlines()
    if not lines:
        raise LifecycleRunError(f"{label} cannot be empty")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if not line:
            raise LifecycleRunError(f"{label} contains an empty row at line {index}")
        row = _load_json_bytes(line, label=f"{label}:{index}")
        if not isinstance(row, dict):
            raise LifecycleRunError(f"{label}:{index} must be a JSON object")
        rows.append(row)
    return rows


def _sidecar_environment(active_slots: int) -> dict[str, str]:
    return {
        "COTCODEC_LIFECYCLE_ACTIVE_SLOTS": str(active_slots),
        "COTCODEC_LIFECYCLE_MAINTENANCE_MODE": "dedupe",
        "COTCODEC_LIFECYCLE_IMPLEMENTATION_KIND": "subprocess_reference",
    }


def _runtime_receipt() -> dict[str, Any]:
    profile = os.environ.get(
        "COTCODEC_LIFECYCLE_RUNTIME",
        "host-development-subprocess-not-container-attested",
    )
    if profile == "host-development-subprocess-not-container-attested":
        containerized = False
        image_id = None
        network_mode = "host"
        source_state = "working-tree-development"
    elif profile == "container-development-network-none-not-publication-attested":
        containerized = True
        image_id = os.environ.get("COTCODEC_CONTAINER_IMAGE_ID")
        if (
            not isinstance(image_id, str)
            or not image_id.startswith("sha256:")
            or len(image_id) != 71
            or any(character not in "0123456789abcdef" for character in image_id[7:])
        ):
            raise LifecycleRunError("contained lifecycle run requires an exact image ID")
        network_mode = os.environ.get("COTCODEC_CONTAINER_NETWORK_MODE")
        if network_mode != "none":
            raise LifecycleRunError("contained lifecycle run must declare network mode none")
        source_state = os.environ.get("COTCODEC_CONTAINER_SOURCE_STATE")
        if source_state not in {
            "dirty-development",
            "clean-unattested-development",
        }:
            raise LifecycleRunError("contained lifecycle source state is not explicit")
    else:
        raise LifecycleRunError(f"unsupported lifecycle runtime profile: {profile}")
    return {
        "profile": profile,
        "containerized": containerized,
        "container_image_id": image_id,
        "network_mode": network_mode,
        "source_state": source_state,
        "scheduler_job_id": os.environ.get("SLURM_JOB_ID"),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "publication_attested": False,
    }


def _command(
    command_id: str,
    *,
    scope: str,
    step: int,
    kind: str,
    event: LifecycleEvent | None = None,
    query: LifecycleQuery | None = None,
) -> LifecycleCommand:
    return LifecycleCommand(
        command_id=command_id,
        idempotency_key=f"{command_id}.idempotency",
        session_scope=scope,
        step=step,
        kind=kind,
        event=event,
        query=query,
    )


def _run_isolation_purge_audit() -> dict[str, Any]:
    sidecar_command = (sys.executable, str(REFERENCE_SIDECAR))
    session_a = "lifecycle-isolation-a"
    session_b = "lifecycle-isolation-b"
    begin_a = _command("audit.begin-a", scope=session_a, step=0, kind="begin")
    write_a = _command(
        "audit.write-a",
        scope=session_a,
        step=1,
        kind="apply",
        event=LifecycleEvent(
            event_id="audit.event.canary",
            step=1,
            kind="write",
            record_id="audit-canary-record",
            entity_id="audit-user-a",
            key="private-canary",
            value="saffron-echo-921",
        ),
    )
    begin_b = _command("audit.begin-b", scope=session_b, step=0, kind="begin")
    query_b = _command(
        "audit.query-b",
        scope=session_b,
        step=1,
        kind="query",
        query=LifecycleQuery(
            query_id="audit-query-b",
            step=1,
            text="audit user private canary saffron echo 921",
            top_k=2,
            max_archive_reads=1,
            max_injected_tokens=256,
        ),
    )
    purge_a = _command("audit.purge-a", scope=session_a, step=2, kind="purge")
    inspect_a = _command("audit.inspect-a", scope=session_a, step=3, kind="inspect")
    replay_rejected = False
    reuse_rejected = False
    with SubprocessLifecyclePort(
        sidecar_command,
        timeout_seconds=10,
        environment=_sidecar_environment(4),
    ) as port:
        port.execute(begin_a)
        port.execute(write_a)
        port.execute(begin_b)
        cross_session = port.execute(query_b)
        port.execute(purge_a)
        purged = port.execute(inspect_a)
        try:
            port.execute(write_a)
        except MemoryLifecycleError:
            replay_rejected = True
        try:
            port.execute(
                _command("audit.reuse-a", scope=session_a, step=4, kind="begin")
            )
        except MemoryLifecycleError:
            reuse_rejected = True
        port.execute(_command("audit.purge-b", scope=session_b, step=2, kind="purge"))
        port.execute(_command("audit.inspect-b", scope=session_b, step=3, kind="inspect"))
    gates = {
        "cross_session_canary_visibility_zero": not cross_session.evidence,
        "purge_active_records_zero": not purged.summary.active_record_ids,
        "purge_archive_records_zero": not purged.summary.archive_record_ids,
        "pre_purge_command_replay_rejected": replay_rejected,
        "purged_session_reuse_rejected": reuse_rejected,
    }
    return {
        "schema_version": 1,
        "canary_sha256": sha256_text("saffron-echo-921"),
        "cross_session_evidence_count": len(cross_session.evidence),
        "gates": gates,
        "status": "PASS" if all(gates.values()) else "FAIL",
    }


def _aggregate_costs(traces: list[dict[str, Any]]) -> dict[str, dict[str, int | float]]:
    fields = (
        "writes",
        "reads",
        "serialized_input_bytes",
        "serialized_output_bytes",
        "injected_tokens_estimate",
        "embedding_calls",
        "llm_calls",
        "latency_ms",
    )
    totals: dict[str, dict[str, int | float]] = defaultdict(
        lambda: {field: 0 for field in fields}
    )
    for trace in traces:
        for cost in trace["phase_costs"]:
            phase = cost["phase"]
            for field in fields:
                totals[phase][field] += cost[field]
    return {phase: dict(values) for phase, values in sorted(totals.items())}


def _checkpoint_row(
    case: LifecycleStudyCase,
    trace: LifecycleTraceReceipt,
    restored_trace: LifecycleTraceReceipt,
) -> dict[str, Any]:
    checkpoint_index = next(
        index
        for index, command in enumerate(case.plan.commands)
        if command.command_id == case.oracle.checkpoint_command_id
    )
    checkpoint = trace.operations[checkpoint_index].checkpoint
    if checkpoint is None:
        raise LifecycleRunError(f"{case.case_id}: missing checkpoint")
    restore_plan = compile_restore_plan(case, trace)
    return {
        "case_id": case.case_id,
        "checkpoint_sha256": checkpoint.checkpoint_sha256,
        "checkpoint_state_sha256": checkpoint.state_sha256,
        "restore_plan_sha256": restore_plan.plan_sha256,
        "uninterrupted_trace_sha256": trace.trace_sha256,
        "restored_trace_sha256": restored_trace.trace_sha256,
        "suffix_operation_receipts_byte_equal": True,
    }


def run_contract(experiment_path: Path) -> dict[str, Any]:
    experiment, experiment_sha256 = load_and_validate_experiment(experiment_path)
    experiment_bytes = experiment_path.read_bytes()
    if _sha256_bytes(experiment_bytes) != experiment_sha256:
        raise LifecycleRunError("experiment bytes changed during validation")
    code_receipt = _code_receipt()
    source = experiment["source"]
    budget = experiment["budget"]
    active_slot_cells = (
        budget["primary_active_slots"],
        *budget["diagnostic_active_slots"],
    )
    cases = compile_lifecycle_matrix(
        episodes_per_slot_cell=source["episodes_per_active_slot_cell"],
        active_slot_cells=active_slot_cells,
        seed=source["seed"],
    )
    sidecar_command = (sys.executable, str(REFERENCE_SIDECAR))
    plans: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    restore_traces: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    system_receipts: dict[str, dict[str, Any]] = {}
    start = time.monotonic()

    for active_slots in active_slot_cells:
        cell_cases = [case for case in cases if case.active_slots == active_slots]
        with SubprocessLifecyclePort(
            sidecar_command,
            timeout_seconds=10,
            environment=_sidecar_environment(active_slots),
        ) as port:
            system_receipts[str(active_slots)] = port.receipt.model_dump(mode="json")
            for case in cell_cases:
                trace = run_lifecycle_plan(port, case.plan)
                restore_plan = compile_restore_plan(case, trace)
                with SubprocessLifecyclePort(
                    sidecar_command,
                    timeout_seconds=10,
                    environment=_sidecar_environment(active_slots),
                ) as restore_port:
                    restored_trace = run_lifecycle_plan(restore_port, restore_plan)
                result = evaluate_lifecycle_case(
                    case,
                    trace,
                    restored_trace=restored_trace,
                )
                plans.append(case.model_dump(mode="json"))
                traces.append(trace.model_dump(mode="json"))
                restore_traces.append(restored_trace.model_dump(mode="json"))
                case_results.append(result)
                checkpoint_rows.append(_checkpoint_row(case, trace, restored_trace))

    isolation_audit = _run_isolation_purge_audit()
    family_counts = Counter(case.family for case in cases)
    cell_counts = Counter(case.active_slots for case in cases)
    gates = {
        "exact_total_trace_count": len(cases) == source["total_trace_count"],
        "exact_active_slot_cell_counts": all(
            cell_counts[cell] == source["episodes_per_active_slot_cell"]
            for cell in active_slot_cells
        ),
        "exact_family_counts": all(
            family_counts[family]
            == source["cases_per_family_per_cell"] * len(active_slot_cells)
            for family in LIFECYCLE_FAMILIES
        ),
        "all_case_gates_pass": all(
            all(bool(value) for value in row["gates"].values())
            for row in case_results
        ),
        "all_checkpoint_suffixes_exact": len(checkpoint_rows) == len(cases)
        and all(row["suffix_operation_receipts_byte_equal"] for row in checkpoint_rows),
        "isolation_and_purge_audit_pass": isolation_audit["status"] == "PASS",
        "system_receipts_non_publication": all(
            receipt["publication_ready"] is False for receipt in system_receipts.values()
        ),
        "no_model_or_gpu_calls": all(
            cost["llm_calls"] == 0 and cost["embedding_calls"] == 0
            for cost in _aggregate_costs(traces).values()
        ),
    }
    failed = sorted(name for name, passed in gates.items() if not passed)
    if failed:
        raise LifecycleRunError(f"registered lifecycle gates failed: {failed}")
    elapsed_seconds = time.monotonic() - start
    costs = _aggregate_costs(traces)
    roots = {
        "ordered_case_root_sha256": ordered_root(row["case_sha256"] for row in case_results),
        "ordered_plan_root_sha256": ordered_root(row["plan_sha256"] for row in case_results),
        "ordered_trace_root_sha256": ordered_root(row["trace_sha256"] for row in case_results),
        "ordered_restore_trace_root_sha256": ordered_root(
            row["restored_trace_sha256"] for row in case_results
        ),
    }
    runtime_receipt = _runtime_receipt()
    report = {
        "schema_version": 1,
        "status": "LIFECYCLE_REFERENCE_CONTRACT_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "reason": (
            "deterministic reference transport and mechanism contract only; "
            "no native memory system or model outcome was evaluated"
        ),
        "experiment_sha256": experiment_sha256,
        "study_version": experiment["study_version"],
        "protocol": experiment["protocol"],
        "runtime": runtime_receipt["profile"],
        "runtime_receipt": runtime_receipt,
        "elapsed_seconds": elapsed_seconds,
        "case_count": len(cases),
        "uninterrupted_trace_count": len(traces),
        "fresh_process_restore_trace_count": len(restore_traces),
        "family_counts": dict(sorted(family_counts.items())),
        "active_slot_cell_counts": {str(key): value for key, value in sorted(cell_counts.items())},
        "system_receipts_by_active_slots": system_receipts,
        "gates": gates,
        "roots": roots,
        "code_root_sha256": sha256_text(canonical_json(code_receipt)),
        "forbidden_claims": experiment["forbidden_claims"],
    }
    return {
        "experiment_bytes": experiment_bytes,
        "experiment_sha256": experiment_sha256,
        "code_receipt": code_receipt,
        "plans": plans,
        "traces": traces,
        "restore_traces": restore_traces,
        "case_results": case_results,
        "checkpoint_audit": {
            "schema_version": 1,
            "status": "PASS",
            "case_count": len(checkpoint_rows),
            "rows": checkpoint_rows,
        },
        "isolation_purge_audit": isolation_audit,
        "costs_by_phase": {
            "schema_version": 1,
            "uninterrupted_trace_count": len(traces),
            "phases": costs,
        },
        "report": report,
    }


def load_and_validate_output(output_dir: Path) -> dict[str, Any]:
    """Recompute a completed lifecycle bundle from bytes and fail closed on drift."""

    if not output_dir.is_dir() or output_dir.is_symlink():
        raise LifecycleRunError("sealed output must be a regular non-symlink directory")
    children = {path.name: path for path in output_dir.iterdir()}
    if set(children) != SEALED_OUTPUT_FILENAMES:
        missing = sorted(SEALED_OUTPUT_FILENAMES - set(children))
        extra = sorted(set(children) - SEALED_OUTPUT_FILENAMES)
        raise LifecycleRunError(
            f"sealed output file roster drifted; missing={missing}, extra={extra}"
        )
    encoded: dict[str, bytes] = {}
    for filename, path in children.items():
        if not path.is_file() or path.is_symlink():
            raise LifecycleRunError(f"sealed output child is not a regular file: {filename}")
        encoded[filename] = path.read_bytes()

    manifest = _load_json_bytes(encoded["manifest.json"], label="manifest.json")
    if not isinstance(manifest, dict):
        raise LifecycleRunError("manifest.json must be a JSON object")
    experiment, experiment_sha256 = load_and_validate_experiment(
        output_dir / "experiment.yaml"
    )
    if _sha256_bytes(encoded["experiment.yaml"]) != experiment_sha256:
        raise LifecycleRunError("sealed experiment bytes changed during validation")
    code_receipt = _code_receipt()
    artifact_receipt = {
        filename: {
            "sha256": _sha256_bytes(encoded[filename]),
            "size": len(encoded[filename]),
        }
        for filename in SEALED_ARTIFACT_FILENAMES
    }
    expected_manifest = {
        "schema_version": 1,
        "status": "SEALED_LIFECYCLE_REFERENCE_CONTRACT",
        "scientific_result": False,
        "publication_ready": False,
        "experiment_sha256": experiment_sha256,
        "code_receipt": code_receipt,
        "artifacts": artifact_receipt,
        "artifact_root_sha256": sha256_text(canonical_json(artifact_receipt)),
        "code_root_sha256": sha256_text(canonical_json(code_receipt)),
    }
    if manifest != expected_manifest:
        raise LifecycleRunError("sealed lifecycle manifest does not bind current bytes")

    plan_rows = _load_jsonl_bytes(encoded["plans.jsonl"], label="plans.jsonl")
    trace_rows = _load_jsonl_bytes(encoded["traces.jsonl"], label="traces.jsonl")
    restore_rows = _load_jsonl_bytes(
        encoded["restore-traces.jsonl"], label="restore-traces.jsonl"
    )
    result_rows = _load_jsonl_bytes(
        encoded["case-results.jsonl"], label="case-results.jsonl"
    )
    source = experiment["source"]
    budget = experiment["budget"]
    active_slot_cells = (
        budget["primary_active_slots"],
        *budget["diagnostic_active_slots"],
    )
    cases = compile_lifecycle_matrix(
        episodes_per_slot_cell=source["episodes_per_active_slot_cell"],
        active_slot_cells=active_slot_cells,
        seed=source["seed"],
    )
    expected_plan_rows = [case.model_dump(mode="json") for case in cases]
    if plan_rows != expected_plan_rows:
        raise LifecycleRunError("sealed lifecycle plans differ from the compiler output")
    try:
        parsed_cases = [LifecycleStudyCase.model_validate(row) for row in plan_rows]
        traces = [LifecycleTraceReceipt.model_validate(row) for row in trace_rows]
        restored_traces = [
            LifecycleTraceReceipt.model_validate(row) for row in restore_rows
        ]
    except Exception as exc:
        raise LifecycleRunError("sealed lifecycle model receipt is invalid") from exc
    expected_count = len(cases)
    if not all(
        len(rows) == expected_count
        for rows in (parsed_cases, traces, restored_traces, result_rows)
    ):
        raise LifecycleRunError("sealed lifecycle row counts differ from the compiler")

    recomputed_results: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    system_receipts: dict[str, dict[str, Any]] = {}
    for case, trace, restored_trace in zip(
        parsed_cases, traces, restored_traces, strict=True
    ):
        if trace.plan_id != case.plan.plan_id or trace.plan_sha256 != case.plan.plan_sha256:
            raise LifecycleRunError(f"{case.case_id}: trace is bound to another plan")
        restore_plan = compile_restore_plan(case, trace)
        if (
            restored_trace.plan_id != restore_plan.plan_id
            or restored_trace.plan_sha256 != restore_plan.plan_sha256
        ):
            raise LifecycleRunError(f"{case.case_id}: restore trace is bound to another plan")
        if restored_trace.system_receipt != trace.system_receipt:
            raise LifecycleRunError(f"{case.case_id}: restore system identity drifted")
        receipt = LifecycleSystemReceipt.model_validate(trace.system_receipt)
        if receipt.system_id != case.plan.expected_system_id:
            raise LifecycleRunError(f"{case.case_id}: trace system identity drifted")
        cell_key = str(case.active_slots)
        receipt_payload = receipt.model_dump(mode="json")
        prior = system_receipts.setdefault(cell_key, receipt_payload)
        if prior != receipt_payload:
            raise LifecycleRunError(f"active-slot cell {cell_key}: system receipt drifted")
        recomputed_results.append(
            evaluate_lifecycle_case(case, trace, restored_trace=restored_trace)
        )
        checkpoint_rows.append(_checkpoint_row(case, trace, restored_trace))
    if result_rows != recomputed_results:
        raise LifecycleRunError("sealed lifecycle case results do not recompute")

    checkpoint_audit = _load_json_bytes(
        encoded["checkpoint-audit.json"], label="checkpoint-audit.json"
    )
    expected_checkpoint_audit = {
        "schema_version": 1,
        "status": "PASS",
        "case_count": expected_count,
        "rows": checkpoint_rows,
    }
    if checkpoint_audit != expected_checkpoint_audit:
        raise LifecycleRunError("sealed checkpoint audit does not recompute")
    isolation_audit = _load_json_bytes(
        encoded["isolation-purge-audit.json"], label="isolation-purge-audit.json"
    )
    expected_isolation_keys = {
        "cross_session_canary_visibility_zero",
        "purge_active_records_zero",
        "purge_archive_records_zero",
        "pre_purge_command_replay_rejected",
        "purged_session_reuse_rejected",
    }
    if not isinstance(isolation_audit, dict) or isolation_audit != {
        "schema_version": 1,
        "canary_sha256": sha256_text("saffron-echo-921"),
        "cross_session_evidence_count": 0,
        "gates": {name: True for name in sorted(expected_isolation_keys)},
        "status": "PASS",
    }:
        raise LifecycleRunError("sealed isolation and purge audit is invalid")

    costs = _aggregate_costs(trace_rows)
    costs_by_phase = _load_json_bytes(
        encoded["costs-by-phase.json"], label="costs-by-phase.json"
    )
    if costs_by_phase != {
        "schema_version": 1,
        "uninterrupted_trace_count": expected_count,
        "phases": costs,
    }:
        raise LifecycleRunError("sealed phase costs do not recompute")

    family_counts = Counter(case.family for case in cases)
    cell_counts = Counter(case.active_slots for case in cases)
    gates = {
        "exact_total_trace_count": expected_count == source["total_trace_count"],
        "exact_active_slot_cell_counts": all(
            cell_counts[cell] == source["episodes_per_active_slot_cell"]
            for cell in active_slot_cells
        ),
        "exact_family_counts": all(
            family_counts[family]
            == source["cases_per_family_per_cell"] * len(active_slot_cells)
            for family in LIFECYCLE_FAMILIES
        ),
        "all_case_gates_pass": all(
            all(bool(value) for value in row["gates"].values())
            for row in recomputed_results
        ),
        "all_checkpoint_suffixes_exact": all(
            row["suffix_operation_receipts_byte_equal"] for row in checkpoint_rows
        ),
        "isolation_and_purge_audit_pass": isolation_audit["status"] == "PASS",
        "system_receipts_non_publication": all(
            receipt["publication_ready"] is False for receipt in system_receipts.values()
        ),
        "no_model_or_gpu_calls": all(
            cost["llm_calls"] == 0 and cost["embedding_calls"] == 0
            for cost in costs.values()
        ),
    }
    if set(gates) != RUNNER_GATE_NAMES or not all(gates.values()):
        raise LifecycleRunError("sealed lifecycle aggregate gates do not pass")
    roots = {
        "ordered_case_root_sha256": ordered_root(
            row["case_sha256"] for row in recomputed_results
        ),
        "ordered_plan_root_sha256": ordered_root(
            row["plan_sha256"] for row in recomputed_results
        ),
        "ordered_trace_root_sha256": ordered_root(
            row["trace_sha256"] for row in recomputed_results
        ),
        "ordered_restore_trace_root_sha256": ordered_root(
            row["restored_trace_sha256"] for row in recomputed_results
        ),
    }
    report = _load_json_bytes(encoded["report.json"], label="report.json")
    if not isinstance(report, dict):
        raise LifecycleRunError("report.json must be a JSON object")
    runtime_receipt = report.get("runtime_receipt")
    runtime_keys = {
        "profile",
        "containerized",
        "container_image_id",
        "network_mode",
        "source_state",
        "scheduler_job_id",
        "python_version",
        "python_implementation",
        "platform_system",
        "platform_machine",
        "publication_attested",
    }
    if not isinstance(runtime_receipt, dict) or set(runtime_receipt) != runtime_keys:
        raise LifecycleRunError("sealed lifecycle runtime receipt schema is invalid")
    for key in (
        "profile",
        "network_mode",
        "source_state",
        "python_version",
        "python_implementation",
        "platform_system",
        "platform_machine",
    ):
        if not isinstance(runtime_receipt[key], str) or not runtime_receipt[key]:
            raise LifecycleRunError(f"sealed lifecycle runtime field is invalid: {key}")
    if runtime_receipt["publication_attested"] is not False:
        raise LifecycleRunError("development lifecycle runtime cannot be publication-attested")
    profile = runtime_receipt["profile"]
    if profile == "host-development-subprocess-not-container-attested":
        if (
            runtime_receipt["containerized"] is not False
            or runtime_receipt["container_image_id"] is not None
            or runtime_receipt["network_mode"] != "host"
            or runtime_receipt["source_state"] != "working-tree-development"
        ):
            raise LifecycleRunError("sealed host lifecycle runtime receipt is inconsistent")
    elif profile == "container-development-network-none-not-publication-attested":
        image_id = runtime_receipt["container_image_id"]
        if (
            runtime_receipt["containerized"] is not True
            or runtime_receipt["network_mode"] != "none"
            or runtime_receipt["source_state"]
            not in {"dirty-development", "clean-unattested-development"}
            or not isinstance(image_id, str)
            or not image_id.startswith("sha256:")
            or len(image_id) != 71
            or any(character not in "0123456789abcdef" for character in image_id[7:])
        ):
            raise LifecycleRunError("sealed container lifecycle runtime receipt is inconsistent")
    else:
        raise LifecycleRunError("sealed lifecycle runtime profile is unsupported")
    if runtime_receipt["scheduler_job_id"] is not None and not isinstance(
        runtime_receipt["scheduler_job_id"], str
    ):
        raise LifecycleRunError("sealed lifecycle scheduler job ID is invalid")
    elapsed_seconds = report.get("elapsed_seconds")
    if (
        isinstance(elapsed_seconds, bool)
        or not isinstance(elapsed_seconds, (int, float))
        or not math.isfinite(elapsed_seconds)
        or elapsed_seconds < 0
    ):
        raise LifecycleRunError("sealed lifecycle elapsed time is invalid")
    report_without_elapsed = dict(report)
    report_without_elapsed.pop("elapsed_seconds", None)
    expected_report = {
        "schema_version": 1,
        "status": "LIFECYCLE_REFERENCE_CONTRACT_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "reason": (
            "deterministic reference transport and mechanism contract only; "
            "no native memory system or model outcome was evaluated"
        ),
        "experiment_sha256": experiment_sha256,
        "study_version": experiment["study_version"],
        "protocol": experiment["protocol"],
        "runtime": profile,
        "runtime_receipt": runtime_receipt,
        "case_count": expected_count,
        "uninterrupted_trace_count": len(traces),
        "fresh_process_restore_trace_count": len(restored_traces),
        "family_counts": dict(sorted(family_counts.items())),
        "active_slot_cell_counts": {
            str(key): value for key, value in sorted(cell_counts.items())
        },
        "system_receipts_by_active_slots": system_receipts,
        "gates": gates,
        "roots": roots,
        "code_root_sha256": sha256_text(canonical_json(code_receipt)),
        "forbidden_claims": experiment["forbidden_claims"],
    }
    if report_without_elapsed != expected_report:
        raise LifecycleRunError("sealed lifecycle report does not recompute")
    return {
        **manifest,
        "manifest_sha256": _sha256_bytes(encoded["manifest.json"]),
        "output_dir": str(output_dir),
    }


def seal_output(output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise LifecycleRunError("output directory must not already exist")
    output_dir.mkdir(parents=True, mode=0o700)
    artifacts: dict[str, bytes] = {
        "experiment.yaml": result["experiment_bytes"],
        "plans.jsonl": _jsonl_bytes(result["plans"]),
        "traces.jsonl": _jsonl_bytes(result["traces"]),
        "restore-traces.jsonl": _jsonl_bytes(result["restore_traces"]),
        "case-results.jsonl": _jsonl_bytes(result["case_results"]),
        "checkpoint-audit.json": _json_bytes(result["checkpoint_audit"]),
        "isolation-purge-audit.json": _json_bytes(result["isolation_purge_audit"]),
        "costs-by-phase.json": _json_bytes(result["costs_by_phase"]),
        "report.json": _json_bytes(result["report"]),
    }
    for filename, encoded in artifacts.items():
        _write_once(output_dir / filename, encoded)
    code_receipt = _code_receipt()
    if code_receipt != result["code_receipt"]:
        raise LifecycleRunError("lifecycle code changed between execution and sealing")
    artifact_receipt = {
        filename: {"sha256": _sha256_bytes(encoded), "size": len(encoded)}
        for filename, encoded in sorted(artifacts.items())
    }
    manifest = {
        "schema_version": 1,
        "status": "SEALED_LIFECYCLE_REFERENCE_CONTRACT",
        "scientific_result": False,
        "publication_ready": False,
        "experiment_sha256": result["experiment_sha256"],
        "code_receipt": code_receipt,
        "artifacts": artifact_receipt,
        "artifact_root_sha256": sha256_text(canonical_json(artifact_receipt)),
        "code_root_sha256": sha256_text(canonical_json(code_receipt)),
    }
    manifest_bytes = _json_bytes(manifest)
    _write_once(output_dir / "manifest.json", manifest_bytes)
    directory_fd = os.open(output_dir, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return load_and_validate_output(output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", nargs="?", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    result = run_contract(args.experiment.resolve())
    output_dir = args.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    sealed = seal_output(output_dir, result)
    if args.require_gates and result["report"]["status"] != "LIFECYCLE_REFERENCE_CONTRACT_PASS":
        return 2
    print(json.dumps(sealed, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
