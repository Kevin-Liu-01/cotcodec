#!/usr/bin/env python3
"""Seal native memory selections once for byte-identical cross-model evaluation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    LONGMEMEVAL_S_FILENAME,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
    LONGMEMEVAL_SCREEN32_RAW_TASK_IDS,
    BM25MemorySystem,
    DenseBGERetrievalMemorySystem,
    FrozenLearnedControlArtifact,
    FrozenMemorySystem,
    FullPrefixCeilingSystem,
    GeneratedMemoryTaskSource,
    LearnedNextUseMemorySystem,
    LexicalMemorySystem,
    LongMemEvalTaskSource,
    LRUMemorySystem,
    MemoryBankDecayMemorySystem,
    MemoryBudget,
    MemoryTaskSource,
    MemPalaceRawSessionMemorySystem,
    NoMemorySystem,
    PersistentSubprocessMemorySystem,
    ProfileExpansionMemorySystem,
    RawLogRRFMemorySystem,
    RecencyMemorySystem,
    ReferenceMemorySystem,
    SubprocessMemorySystem,
    TemporalGraphMemorySystem,
    build_memory_system_request,
    run_memory_system,
    task_manifest_sha256,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.fetch_open_model import (  # noqa: E402
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
)

REFERENCE_SYSTEMS = {
    "bm25": BM25MemorySystem,
    "full-prefix-ceiling": FullPrefixCeilingSystem,
    "no-memory": NoMemorySystem,
    "profile-expansion": ProfileExpansionMemorySystem,
    "raw-log-rrf": RawLogRRFMemorySystem,
    "reference": ReferenceMemorySystem,
    "recency": RecencyMemorySystem,
    "lexical": LexicalMemorySystem,
    "lru": LRUMemorySystem,
    "memorybank-corrected": MemoryBankDecayMemorySystem,
    "memorybank-upstream-precedence": lambda: MemoryBankDecayMemorySystem(
        formula="upstream-precedence"
    ),
    "memorybank-no-decay": lambda: MemoryBankDecayMemorySystem(formula="no-decay"),
    "temporal-graph": TemporalGraphMemorySystem,
}
LEARNED_SYSTEM_ID = "learned-next-use"
DENSE_SYSTEM_ID = "dense-bge-retrieval"
MEMPALACE_SYSTEM_ID = "mempalace-raw-session"
AVAILABLE_SYSTEM_IDS = (
    *REFERENCE_SYSTEMS,
    LEARNED_SYSTEM_ID,
    DENSE_SYSTEM_ID,
    MEMPALACE_SYSTEM_ID,
)
SYSTEM_IDENTITIES = {
    **{control_id: factory().identity for control_id, factory in REFERENCE_SYSTEMS.items()},
    LEARNED_SYSTEM_ID: "learned-next-use-memory-v1",
    DENSE_SYSTEM_ID: DenseBGERetrievalMemorySystem.identity,
    MEMPALACE_SYSTEM_ID: MemPalaceRawSessionMemorySystem.identity,
}
DEFAULT_LONGMEMEVAL_PATH = (
    PROJECT_ROOT
    / "data"
    / "benchmarks"
    / "longmemeval"
    / LONGMEMEVAL_DATASET_REVISION
    / LONGMEMEVAL_S_FILENAME
)


def _load_command(raw: str) -> tuple[str, ...]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("sidecar command must be a JSON argv array") from exc
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError("sidecar command must contain non-empty argv strings")
    return tuple(value)


def _load_environment(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read sidecar environment: {path}") from exc
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and key and isinstance(item, str)
        for key, item in value.items()
    ):
        raise ValueError("sidecar environment must be a string-to-string JSON object")
    return value


def _make_system(
    reference_system: str | None,
    sidecar_command_json: str | None,
    sidecar_environment: Mapping[str, str],
    learned_artifact_path: Path | None = None,
    dense_system: DenseBGERetrievalMemorySystem | None = None,
    mempalace_system: Any | None = None,
    persistent_sidecar: bool = False,
) -> Any:
    if (reference_system is None) == (sidecar_command_json is None):
        raise ValueError("select exactly one reference system or sidecar command")
    if reference_system is not None:
        if persistent_sidecar:
            raise ValueError("--persistent-sidecar is valid only for sidecar systems")
        if reference_system == DENSE_SYSTEM_ID:
            if learned_artifact_path is not None:
                raise ValueError("dense-bge-retrieval cannot use --learned-artifact")
            if dense_system is None:
                raise ValueError("dense-bge-retrieval requires a verified BGE model")
            return dense_system
        if reference_system == MEMPALACE_SYSTEM_ID:
            if learned_artifact_path is not None:
                raise ValueError("mempalace-raw-session cannot use --learned-artifact")
            if mempalace_system is None:
                raise ValueError(
                    "mempalace-raw-session requires a verified equivalence control"
                )
            return mempalace_system
        if reference_system == LEARNED_SYSTEM_ID:
            if learned_artifact_path is None:
                raise ValueError("learned-next-use requires --learned-artifact")
            try:
                payload = json.loads(learned_artifact_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"cannot read learned-control artifact: {learned_artifact_path}"
                ) from exc
            return LearnedNextUseMemorySystem(
                FrozenLearnedControlArtifact.model_validate(payload)
            )
        if learned_artifact_path is not None:
            raise ValueError("--learned-artifact is valid only for learned-next-use")
        return REFERENCE_SYSTEMS[reference_system]()
    if learned_artifact_path is not None:
        raise ValueError("sidecar systems cannot use --learned-artifact")
    sidecar_type = (
        PersistentSubprocessMemorySystem if persistent_sidecar else SubprocessMemorySystem
    )
    return sidecar_type(
        _load_command(sidecar_command_json or ""),
        timeout_seconds=600,
        environment=sidecar_environment,
    )


def make_task_source(
    task_source: str,
    *,
    budget: MemoryBudget,
    episodes: int | None,
    source_seed: int,
    candidate_seed: int,
    longmemeval_path: Path,
) -> MemoryTaskSource:
    if task_source == "generated":
        if episodes is None:
            raise ValueError("episodes is required for the generated task source")
        return GeneratedMemoryTaskSource(
            seed=source_seed,
            episode_count=episodes,
            budget=budget,
        )
    if task_source == "longmemeval":
        return LongMemEvalTaskSource(
            longmemeval_path,
            expected_sha256=LONGMEMEVAL_S_SHA256,
            expected_size=LONGMEMEVAL_S_SIZE,
            candidate_seed=candidate_seed,
            budget=budget,
            artifact_role=LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
            task_ids=(
                LONGMEMEVAL_SCREEN32_RAW_TASK_IDS
                if episodes == len(LONGMEMEVAL_SCREEN32_RAW_TASK_IDS)
                else None
            ),
            limit=(
                episodes
                if episodes != len(LONGMEMEVAL_SCREEN32_RAW_TASK_IDS)
                else None
            ),
        )
    raise ValueError(f"unsupported task source: {task_source}")


def compile_bundle(
    system: Any,
    source: MemoryTaskSource,
    *,
    treatment_modes: Sequence[str],
) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    for task_id in source.ids():
        task = source.load(task_id)
        for treatment_mode in treatment_modes:
            for visibility in ("serve", "holdout"):
                request, _expected_value = build_memory_system_request(
                    task,
                    visibility=visibility,
                    treatment_mode=treatment_mode,
                )
                request_sha256 = sha256_text(
                    canonical_json(request.model_dump(mode="json"))
                )
                if request_sha256 in entries:
                    continue
                purge = getattr(system, "purge", None)
                if callable(purge):
                    # Every frozen request is a distinct counterfactual input.
                    # A persistent sidecar must not carry a served candidate into
                    # the following holdout request (or vice versa).
                    purge(task.session_id)
                selection = system.select(request)
                if selection.request_id != request.request_id:
                    raise ValueError("native system returned a selection for another request")
                if selection.receipt != system.receipt:
                    raise ValueError("native system changed its receipt while freezing")
                entries[request_sha256] = {
                    "request_sha256": request_sha256,
                    "request": request.model_dump(mode="json"),
                    "selection": selection.model_dump(mode="json"),
                }
        purge = getattr(system, "purge", None)
        if callable(purge):
            purge(task.session_id)
    payload = {
        "schema_version": "1.0",
        "protocol": "memory-system-v1",
        "status": "FROZEN_SELECTION_BUNDLE",
        "scientific_result": False,
        "reason": (
            "Reproducibility artifact only; actor-model comparisons provide outcomes."
        ),
        "upstream_receipt": system.receipt.model_dump(mode="json"),
        "task_source": {
            **source.provenance,
            "budget": source.budget.model_dump(mode="json"),
            "task_manifest_sha256": task_manifest_sha256(source),
        },
        "treatment_modes": list(treatment_modes),
        "entries": [entries[key] for key in sorted(entries)],
    }
    admission_evidence = getattr(system, "admission_evidence", None)
    if admission_evidence is not None:
        if hasattr(admission_evidence, "model_dump"):
            rendered_admission_evidence = admission_evidence.model_dump(mode="json")
        elif isinstance(admission_evidence, Mapping):
            rendered_admission_evidence = dict(admission_evidence)
        else:
            raise ValueError("memory-system admission evidence is not serializable")
        payload["admission_evidence"] = rendered_admission_evidence
    return {
        **payload,
        "bundle_sha256": sha256_text(canonical_json(payload)),
    }


def write_validated_bundle(
    output: Path,
    payload: Mapping[str, Any],
    *,
    source: MemoryTaskSource,
    treatment_modes: Sequence[str],
) -> FrozenMemorySystem:
    output = Path(os.path.abspath(os.fspath(output)))
    for component in (output, *output.parents):
        if component.is_symlink():
            raise ValueError(
                f"frozen bundle output cannot contain symbolic links: {component}"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f"refusing to overwrite frozen bundle: {output}")
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    encoded = (canonical_json(payload) + "\n").encode()
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    frozen = FrozenMemorySystem(temporary)
    for task_id in source.ids():
        task = source.load(task_id)
        for treatment_mode in treatment_modes:
            for visibility in ("serve", "holdout"):
                run_memory_system(
                    frozen,
                    task,
                    visibility=visibility,
                    treatment_mode=treatment_mode,
                )
    os.replace(temporary, output)
    directory_fd = os.open(output.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return FrozenMemorySystem(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    system_group = parser.add_mutually_exclusive_group(required=True)
    system_group.add_argument("--reference-system", choices=AVAILABLE_SYSTEM_IDS)
    system_group.add_argument("--sidecar-command-json")
    parser.add_argument("--persistent-sidecar", action="store_true")
    parser.add_argument("--learned-artifact", type=Path)
    parser.add_argument("--model-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--mempalace-source-root", type=Path)
    parser.add_argument("--mempalace-equivalence-root", type=Path)
    parser.add_argument("--mempalace-equivalence-contract-sha256")
    parser.add_argument("--mempalace-equivalence-bundle-root-sha256")
    parser.add_argument("--mempalace-direct-runtime-receipt", type=Path)
    parser.add_argument("--mempalace-direct-runtime-receipt-sha256")
    parser.add_argument("--mempalace-port-runtime-receipt", type=Path)
    parser.add_argument("--mempalace-port-runtime-receipt-sha256")
    parser.add_argument("--sidecar-environment-json", type=Path)
    parser.add_argument(
        "--task-source",
        choices=("generated", "longmemeval"),
        default="generated",
    )
    parser.add_argument("--episodes", type=int)
    parser.add_argument("--source-seed", type=int, default=7)
    parser.add_argument("--candidate-seed", type=int, default=42)
    parser.add_argument(
        "--longmemeval-path",
        type=Path,
        default=DEFAULT_LONGMEMEVAL_PATH,
    )
    parser.add_argument(
        "--treatment-mode",
        choices=("storage_and_service", "serve_only", "both"),
        default="storage_and_service",
    )
    parser.add_argument("--active-slots", type=int, default=4)
    parser.add_argument("--max-archive-reads", type=int, default=1)
    parser.add_argument("--retrieval-top-k", type=int, default=4)
    parser.add_argument("--max-injected-tokens", type=int, default=256)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    modes = (
        ("storage_and_service", "serve_only")
        if args.treatment_mode == "both"
        else (args.treatment_mode,)
    )
    budget = MemoryBudget(
        active_slots=args.active_slots,
        max_archive_reads=args.max_archive_reads,
        retrieval_top_k=args.retrieval_top_k,
        max_injected_tokens=args.max_injected_tokens,
    )
    try:
        source = make_task_source(
            args.task_source,
            budget=budget,
            episodes=args.episodes,
            source_seed=args.source_seed,
            candidate_seed=args.candidate_seed,
            longmemeval_path=args.longmemeval_path,
        )
    except ValueError as exc:
        parser.error(str(exc))
    dense_system = None
    if args.reference_system == DENSE_SYSTEM_ID:
        from scripts.dense_bge_factory import build_dense_bge_system

        dense_system = build_dense_bge_system(
            registry_path=args.model_registry,
            model_root=args.model_root,
            receipt_root=args.receipt_root,
        )
    mempalace_system = None
    if args.reference_system == MEMPALACE_SYSTEM_ID:
        required = {
            "--mempalace-source-root": args.mempalace_source_root,
            "--mempalace-equivalence-root": args.mempalace_equivalence_root,
            "--mempalace-equivalence-contract-sha256": (
                args.mempalace_equivalence_contract_sha256
            ),
            "--mempalace-equivalence-bundle-root-sha256": (
                args.mempalace_equivalence_bundle_root_sha256
            ),
            "--mempalace-direct-runtime-receipt": (
                args.mempalace_direct_runtime_receipt
            ),
            "--mempalace-direct-runtime-receipt-sha256": (
                args.mempalace_direct_runtime_receipt_sha256
            ),
            "--mempalace-port-runtime-receipt": args.mempalace_port_runtime_receipt,
            "--mempalace-port-runtime-receipt-sha256": (
                args.mempalace_port_runtime_receipt_sha256
            ),
        }
        missing = [flag for flag, value in required.items() if value is None]
        if missing:
            parser.error(
                "mempalace-raw-session is missing required inputs: "
                + ", ".join(missing)
            )
        from scripts.mempalace_control_factory import (
            build_verified_mempalace_control,
        )

        mempalace_system = build_verified_mempalace_control(
            source_root=args.mempalace_source_root,
            equivalence_root=args.mempalace_equivalence_root,
            expected_equivalence_contract_sha256=(
                args.mempalace_equivalence_contract_sha256
            ),
            expected_equivalence_bundle_root_sha256=(
                args.mempalace_equivalence_bundle_root_sha256
            ),
            direct_runtime_receipt_path=args.mempalace_direct_runtime_receipt,
            expected_direct_runtime_receipt_sha256=(
                args.mempalace_direct_runtime_receipt_sha256
            ),
            port_runtime_receipt_path=args.mempalace_port_runtime_receipt,
            expected_port_runtime_receipt_sha256=(
                args.mempalace_port_runtime_receipt_sha256
            ),
        )
    system = _make_system(
        args.reference_system,
        args.sidecar_command_json,
        _load_environment(args.sidecar_environment_json),
        args.learned_artifact,
        dense_system,
        mempalace_system,
        args.persistent_sidecar,
    )
    try:
        payload = compile_bundle(system, source, treatment_modes=modes)
        frozen = write_validated_bundle(
            args.output,
            payload,
            source=source,
            treatment_modes=modes,
        )
    finally:
        close = getattr(system, "close", None)
        if callable(close):
            close()
    print(
        "frozen memory selections PASS: "
        f"system={frozen.identity} selections={frozen.metadata['selection_count']} "
        f"bundle={frozen.bundle_sha256} output={frozen.path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
