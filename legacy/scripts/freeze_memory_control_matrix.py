#!/usr/bin/env python3
"""Freeze a matched matrix of deterministic memory controls on one task source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    DenseBGERetrievalMemorySystem,
    EventKind,
    FrozenLearnedControlArtifact,
    LearnedNextUseMemorySystem,
    MemoryBudget,
    task_manifest_sha256,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.freeze_memory_system_outputs import (  # noqa: E402
    AVAILABLE_SYSTEM_IDS,
    DEFAULT_LONGMEMEVAL_PATH,
    DENSE_SYSTEM_ID,
    MEMPALACE_SYSTEM_ID,
    REFERENCE_SYSTEMS,
    compile_bundle,
    make_task_source,
    write_validated_bundle,
)

DEFAULT_SYSTEMS = (
    "no-memory",
    "recency",
    "lru",
    "lexical",
    "bm25",
    DENSE_SYSTEM_ID,
    "raw-log-rrf",
    "profile-expansion",
    "temporal-graph",
    "reference",
)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze_control_matrix(
    output_dir: Path,
    *,
    source,
    system_ids: tuple[str, ...] = DEFAULT_SYSTEMS,
    treatment_modes: tuple[str, ...] = ("storage_and_service",),
    learned_artifact: FrozenLearnedControlArtifact | None = None,
    dense_system: DenseBGERetrievalMemorySystem | None = None,
    mempalace_system: Any | None = None,
) -> dict[str, Any]:
    """Build every control from one source object and publish atomically."""

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite control matrix: {output_dir}")
    if not system_ids or len(system_ids) != len(set(system_ids)):
        raise ValueError("control system IDs must be non-empty and unique")
    unknown = set(system_ids) - set(AVAILABLE_SYSTEM_IDS)
    if unknown:
        raise ValueError(f"unknown control systems: {sorted(unknown)}")
    if not treatment_modes or len(treatment_modes) != len(set(treatment_modes)):
        raise ValueError("treatment modes must be non-empty and unique")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        bundles_dir = staging / "bundles"
        bundles_dir.mkdir()
        exact_task_manifest = task_manifest_sha256(source)
        event_kinds = Counter(
            event.kind.value
            for task_id in source.ids()
            for event in source.load(task_id).events
        )
        controls: list[dict[str, Any]] = []
        for system_id in system_ids:
            if system_id == DENSE_SYSTEM_ID:
                if dense_system is None:
                    raise ValueError(
                        "dense-bge-retrieval matrix cell requires a verified BGE model"
                    )
                system = dense_system
            elif system_id == MEMPALACE_SYSTEM_ID:
                if mempalace_system is None:
                    raise ValueError(
                        "mempalace-raw-session matrix cell requires a verified "
                        "equivalence control"
                    )
                system = mempalace_system
            elif system_id == "learned-next-use":
                if learned_artifact is None:
                    raise ValueError(
                        "learned-next-use matrix cell requires a frozen learned artifact"
                    )
                system = LearnedNextUseMemorySystem(learned_artifact)
            else:
                system = REFERENCE_SYSTEMS[system_id]()
            bundle_path = bundles_dir / f"{system_id}.json"
            payload = compile_bundle(system, source, treatment_modes=treatment_modes)
            frozen = write_validated_bundle(
                bundle_path,
                payload,
                source=source,
                treatment_modes=treatment_modes,
            )
            frozen.require_compatible(
                source_provenance=source.provenance,
                budget=source.budget.model_dump(mode="json"),
                treatment_mode=treatment_modes[0],
                exact_task_manifest_sha256=exact_task_manifest,
            )
            access_identified = event_kinds[EventKind.ACCESS.value] > 0
            diagnostic_only = system_id in {"full-prefix-ceiling", "reference"}
            controls.append(
                {
                    "control_id": system_id,
                    "system_id": frozen.receipt.system_id,
                    "implementation_revision": frozen.receipt.implementation_revision,
                    "bundle_path": f"bundles/{system_id}.json",
                    # `bundle_sha256` is retained as the frozen-format semantic
                    # identity for older analysis readers. Publication admission
                    # must carry the semantic and byte digests separately.
                    "bundle_sha256": frozen.bundle_sha256,
                    "bundle_semantic_sha256": frozen.bundle_sha256,
                    "bundle_file_sha256": _sha256_file(bundle_path),
                    "selection_count": frozen.metadata["selection_count"],
                    "training_artifact_sha256": (
                        learned_artifact.artifact_sha256
                        if system_id == "learned-next-use"
                        and learned_artifact is not None
                        else None
                    ),
                    "external_evidence": (
                        mempalace_system.admission_evidence.model_dump(mode="json")
                        if system_id == MEMPALACE_SYSTEM_ID
                        else None
                    ),
                    "budget_class": (
                        "diagnostic-unmatched"
                        if system_id == "full-prefix-ceiling"
                        else "matched"
                    ),
                    "eligible_for_primary": not diagnostic_only
                    and (system_id != "lru" or access_identified),
                    "ineligibility_reason": (
                        "benchmark-has-no-explicit-access-events"
                        if system_id == "lru" and not access_identified
                        else "unmatched-full-prefix-ceiling"
                        if system_id == "full-prefix-ceiling"
                        else "task-blind-hybrid-diagnostic-only"
                        if system_id == "reference"
                        else None
                    ),
                }
            )
        unsigned = {
            "schema_version": 1,
            "status": "FROZEN_CONTROL_MATRIX",
            "scientific_result": False,
            "reason": (
                "Selection/provenance artifact only; no actor outcome or memory-policy "
                "claim."
            ),
            "task_source": {
                **source.provenance,
                "budget": source.budget.model_dump(mode="json"),
                "task_manifest_sha256": exact_task_manifest,
            },
            "event_kind_counts": dict(sorted(event_kinds.items())),
            "treatment_modes": list(treatment_modes),
            "controls": controls,
        }
        manifest = {
            **unsigned,
            "matrix_sha256": sha256_text(canonical_json(unsigned)),
        }
        _write_json(staging / "manifest.json", manifest)
        _fsync_directory(bundles_dir)
        _fsync_directory(staging)
        os.replace(staging, output_dir)
        _fsync_directory(output_dir.parent)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
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
        "--systems",
        nargs="+",
        choices=AVAILABLE_SYSTEM_IDS,
        default=DEFAULT_SYSTEMS,
    )
    parser.add_argument("--learned-artifact", type=Path)
    parser.add_argument("--model-registry", type=Path)
    parser.add_argument("--model-root", type=Path)
    parser.add_argument("--receipt-root", type=Path)
    parser.add_argument("--mempalace-source-root", type=Path)
    parser.add_argument("--mempalace-equivalence-root", type=Path)
    parser.add_argument("--mempalace-equivalence-contract-sha256")
    parser.add_argument("--mempalace-equivalence-bundle-root-sha256")
    parser.add_argument("--mempalace-direct-runtime-receipt", type=Path)
    parser.add_argument("--mempalace-direct-runtime-receipt-sha256")
    parser.add_argument("--mempalace-port-runtime-receipt", type=Path)
    parser.add_argument("--mempalace-port-runtime-receipt-sha256")
    parser.add_argument(
        "--treatment-mode",
        choices=("storage_and_service", "serve_only", "both"),
        default="storage_and_service",
    )
    parser.add_argument("--active-slots", type=int, default=4)
    parser.add_argument("--max-archive-reads", type=int, default=1)
    parser.add_argument("--retrieval-top-k", type=int, default=4)
    parser.add_argument("--max-injected-tokens", type=int, default=256)
    args = parser.parse_args()
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
        modes = (
            ("storage_and_service", "serve_only")
            if args.treatment_mode == "both"
            else (args.treatment_mode,)
        )
        learned_artifact = None
        if args.learned_artifact is not None:
            learned_artifact = FrozenLearnedControlArtifact.model_validate_json(
                args.learned_artifact.read_text(encoding="utf-8")
            )
        dense_system = None
        if DENSE_SYSTEM_ID in args.systems:
            from scripts.dense_bge_factory import build_dense_bge_system
            from scripts.fetch_open_model import (
                DEFAULT_MODEL_ROOT,
                DEFAULT_RECEIPT_ROOT,
                DEFAULT_REGISTRY,
            )

            dense_system = build_dense_bge_system(
                registry_path=args.model_registry or DEFAULT_REGISTRY,
                model_root=args.model_root or DEFAULT_MODEL_ROOT,
                receipt_root=args.receipt_root or DEFAULT_RECEIPT_ROOT,
            )
        mempalace_system = None
        if MEMPALACE_SYSTEM_ID in args.systems:
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
                "--mempalace-port-runtime-receipt": (
                    args.mempalace_port_runtime_receipt
                ),
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
        manifest = freeze_control_matrix(
            args.output_dir,
            source=source,
            system_ids=tuple(args.systems),
            treatment_modes=modes,
            learned_artifact=learned_artifact,
            dense_system=dense_system,
            mempalace_system=mempalace_system,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
