#!/usr/bin/env python3
"""Run the real-BGE frozen ReasoningBank procedural-bank CPU doctor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.procedural_bank import (  # noqa: E402
    FrozenProceduralBankRetriever,
    ProceduralBankItemInput,
    ProceduralQuery,
    ProceduralTaskRef,
    freeze_procedural_bank,
    seal_procedural_split_manifest,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.dense_bge_factory import build_dense_bge_embedding  # noqa: E402

STATUS = "FROZEN_PROCEDURAL_BANK_CPU_DOCTOR_PASS"


class DoctorError(RuntimeError):
    """Raised when the contained procedural-bank contract fails."""


def _sha_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise DoctorError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (canonical_json(row) + "\n").encode("utf-8") for row in rows
    )


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise DoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _item(
    task_id: str,
    family_id: str,
    query: str,
    procedure: str,
    outcome: Literal["success", "failure"],
) -> ProceduralBankItemInput:
    trajectory, correctness, generator = _fixture_receipt_payloads(
        task_id=task_id,
        family_id=family_id,
        query=query,
        procedure=procedure,
        outcome=outcome,
    )
    return ProceduralBankItemInput(
        source_task_id=task_id,
        source_family_id=family_id,
        source_query=query,
        outcome=outcome,
        procedural_text=procedure,
        source_trajectory_sha256=sha256_text(canonical_json(trajectory)),
        correctness_receipt_sha256=sha256_text(canonical_json(correctness)),
        generator_receipt_sha256=sha256_text(canonical_json(generator)),
    )


def _fixture_receipt_payloads(
    *,
    task_id: str,
    family_id: str,
    query: str,
    procedure: str,
    outcome: Literal["success", "failure"],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    trajectory = {
        "schema_version": "procedural-fixture-trajectory-v1",
        "task_id": task_id,
        "workflow_family_id": family_id,
        "source_query": query,
        "framework_visible_steps": [
            {
                "step": 1,
                "role": "assistant",
                "content": procedure,
            }
        ],
    }
    correctness = {
        "schema_version": "procedural-fixture-correctness-v1",
        "task_id": task_id,
        "evaluator": "deterministic-fixture-v1",
        "outcome": outcome,
    }
    generator = {
        "schema_version": "procedural-fixture-generator-v1",
        "task_id": task_id,
        "generator_kind": "hand-authored-fixture",
        "model_id": None,
        "api_calls": 0,
    }
    return trajectory, correctness, generator


def _fixture_source_artifact_rows(
    items: tuple[ProceduralBankItemInput, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda value: value.source_task_id):
        trajectory, correctness, generator = _fixture_receipt_payloads(
            task_id=item.source_task_id,
            family_id=item.source_family_id,
            query=item.source_query,
            procedure=item.procedural_text,
            outcome=item.outcome,
        )
        row = {
            "source_task_id": item.source_task_id,
            "trajectory": trajectory,
            "trajectory_sha256": sha256_text(canonical_json(trajectory)),
            "correctness_receipt": correctness,
            "correctness_receipt_sha256": sha256_text(canonical_json(correctness)),
            "generator_receipt": generator,
            "generator_receipt_sha256": sha256_text(canonical_json(generator)),
        }
        if (
            row["trajectory_sha256"] != item.source_trajectory_sha256
            or row["correctness_receipt_sha256"]
            != item.correctness_receipt_sha256
            or row["generator_receipt_sha256"] != item.generator_receipt_sha256
        ):
            raise DoctorError("fixture source artifact does not bind its bank item")
        rows.append(row)
    return rows


def _fixture() -> tuple[
    tuple[ProceduralBankItemInput, ...],
    Any,
    tuple[tuple[ProceduralQuery, str], ...],
]:
    items = (
        _item(
            "train-db-reset",
            "relational-database-credential-rotation",
            "reset a postgres database password safely",
            "Confirm the target role, rotate its credential, then verify a fresh login.",
            "failure",
        ),
        _item(
            "train-db-migration",
            "relational-database-schema-rollback",
            "roll back a failed database schema migration",
            "Stop writes, restore the prior schema, then validate application reads.",
            "success",
        ),
        _item(
            "train-travel-flight",
            "international-air-travel-purchase",
            "book an international airline flight",
            "Compare dates and fare rules, confirm identity details, then book once.",
            "success",
        ),
        _item(
            "train-travel-hotel",
            "lodging-reservation-cancellation",
            "cancel a hotel reservation without a penalty",
            "Read the cancellation deadline, confirm the booking, then request cancellation.",
            "failure",
        ),
        _item(
            "train-git-recover",
            "distributed-version-control-object-recovery",
            "recover a git commit after an accidental reset",
            "Inspect reflog, create a recovery branch at the lost commit, then verify the diff.",
            "success",
        ),
        _item(
            "train-git-conflict",
            "distributed-version-control-merge-resolution",
            "resolve a git merge conflict without losing changes",
            "Inspect both sides, edit only conflict regions, test, then commit the resolution.",
            "failure",
        ),
    )
    split = seal_procedural_split_manifest(
        train=tuple(
            ProceduralTaskRef(
                task_id=item.source_task_id,
                workflow_family_id=item.source_family_id,
            )
            for item in items
        ),
        dev=(
            ProceduralTaskRef(
                task_id="dev-secret-rotation",
                workflow_family_id="cloud-service-account-secret-rotation",
            ),
            ProceduralTaskRef(
                task_id="dev-document-recovery",
                workflow_family_id="document-version-history-recovery",
            ),
            ProceduralTaskRef(
                task_id="dev-rental-reservation",
                workflow_family_id="vehicle-rental-reservation",
            ),
        ),
        test=(
            ProceduralTaskRef(
                task_id="test-certificate-renewal",
                workflow_family_id="public-key-certificate-renewal",
            ),
            ProceduralTaskRef(
                task_id="test-object-recovery",
                workflow_family_id="object-store-version-recovery",
            ),
            ProceduralTaskRef(
                task_id="test-conference-registration",
                workflow_family_id="conference-registration-purchase",
            ),
        ),
    )
    queries = (
        (
            ProceduralQuery(
                request_id="dev-secret-rotation-request",
                task_id="dev-secret-rotation",
                workflow_family_id="cloud-service-account-secret-rotation",
                split="dev",
                text="rotate a cloud service account secret and verify new authentication",
                top_k=1,
                max_injected_tokens=96,
            ),
            "train-db-reset",
        ),
        (
            ProceduralQuery(
                request_id="dev-document-recovery-request",
                task_id="dev-document-recovery",
                workflow_family_id="document-version-history-recovery",
                split="dev",
                text=(
                    "recover a deleted document version from history, create a recovery "
                    "copy, then verify the diff"
                ),
                top_k=1,
                max_injected_tokens=96,
            ),
            "train-git-recover",
        ),
        (
            ProceduralQuery(
                request_id="dev-rental-reservation-request",
                task_id="dev-rental-reservation",
                workflow_family_id="vehicle-rental-reservation",
                split="dev",
                text="reserve a rental car after comparing dates and cancellation rules",
                top_k=1,
                max_injected_tokens=96,
            ),
            "train-travel-flight",
        ),
        (
            ProceduralQuery(
                request_id="test-certificate-renewal-request",
                task_id="test-certificate-renewal",
                workflow_family_id="public-key-certificate-renewal",
                split="test",
                text="replace a TLS certificate private key and verify clients authenticate",
                top_k=1,
                max_injected_tokens=96,
            ),
            "train-db-reset",
        ),
        (
            ProceduralQuery(
                request_id="test-object-recovery-request",
                task_id="test-object-recovery",
                workflow_family_id="object-store-version-recovery",
                split="test",
                text="recover an overwritten object from versioned storage and verify the diff",
                top_k=1,
                max_injected_tokens=96,
            ),
            "train-git-recover",
        ),
        (
            ProceduralQuery(
                request_id="test-conference-registration-request",
                task_id="test-conference-registration",
                workflow_family_id="conference-registration-purchase",
                split="test",
                text="purchase a conference registration after checking dates and refund rules",
                top_k=1,
                max_injected_tokens=96,
            ),
            "train-travel-flight",
        ),
    )
    return items, split, queries


def run_doctor(
    *,
    registry: Path,
    model_root: Path,
    receipt_root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    import torch
    import transformers

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    embedding = build_dense_bge_embedding(
        registry_path=registry,
        model_root=model_root,
        receipt_root=receipt_root,
    )
    items, split, queries = _fixture()
    first_bank = freeze_procedural_bank(
        items,
        split_manifest=split,
        embedding=embedding,
    )
    second_bank = freeze_procedural_bank(
        items,
        split_manifest=split,
        embedding=embedding,
    )
    if first_bank != second_bank:
        raise DoctorError("repeated bank freezes differ")
    retriever = FrozenProceduralBankRetriever(first_bank, embedding)
    bank_before = canonical_json(first_bank.model_dump(mode="json"))
    retrievals: list[dict[str, Any]] = []
    top_one_correct = 0
    for query, expected_source_task in queries:
        first = retriever.retrieve(query)
        second = retriever.retrieve(query)
        if first != second:
            raise DoctorError(f"repeated retrieval differs: {query.request_id}")
        if not first.hits or first.hits[0].source_task_id != expected_source_task:
            raise DoctorError(f"unexpected top-1 procedure: {query.request_id}")
        top_one_correct += 1
        retrievals.append(
            {
                "query": query.model_dump(mode="json"),
                "expected_source_task_id": expected_source_task,
                "retrieval": first.model_dump(mode="json"),
            }
        )
    if canonical_json(first_bank.model_dump(mode="json")) != bank_before:
        raise DoctorError("retrieval mutated the frozen bank")
    try:
        retriever.retrieve(
            ProceduralQuery(
                request_id="negative-train-request",
                task_id="train-db-reset",
                workflow_family_id="relational-database-credential-rotation",
                split="test",
                text="reset postgres password",
            )
        )
    except ValueError as exc:
        train_leakage_rejected = "TRAIN bank" in str(exc)
    else:
        train_leakage_rejected = False
    try:
        retriever.retrieve(
            ProceduralQuery(
                request_id="negative-pair-request",
                task_id="test-certificate-renewal",
                workflow_family_id="conference-registration-purchase",
                split="test",
                text="reset postgres password",
            )
        )
    except ValueError as exc:
        task_family_mismatch_rejected = "task/family pair" in str(exc)
    else:
        task_family_mismatch_rejected = False
    if not train_leakage_rejected or not task_family_mismatch_rejected:
        raise DoctorError("split leakage negative controls did not fail closed")
    bank = first_bank.model_dump(mode="json")
    fixture_source_artifacts = _fixture_source_artifact_rows(items)
    report = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "evidence_role": "contained-real-encoder-contract-only",
        "model": embedding.identity.model_dump(mode="json"),
        "document_text_field": first_bank.document_text_field,
        "bank_artifact_sha256": first_bank.artifact_sha256,
        "split_manifest_sha256": split.manifest_sha256,
        "train_items": len(first_bank.items),
        "evaluation_queries": len(queries),
        "top_one_correct": top_one_correct,
        "repeated_bank_freeze_exact": True,
        "repeated_retrieval_exact": True,
        "retrieval_bank_immutable": True,
        "train_task_leakage_rejected": train_leakage_rejected,
        "task_family_mismatch_rejected": task_family_mismatch_rejected,
        "fixture_source_artifacts": len(fixture_source_artifacts),
        "fixture_receipts_only": True,
        "real_reasoningbank_trajectories_present": False,
        "network_required": False,
        "api_calls": 0,
        "gpus": 0,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "torch_threads": torch.get_num_threads(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        },
        "limitations": [
            "synthetic retrieval fixtures, not agent-task quality evidence",
            "procedures are fixture text, not regenerated from ReasoningBank trajectories",
            "no matched actor or procedural-memory control matrix was executed",
            "local Docker evidence is not external Slurm or publication attestation",
        ],
    }
    return report, bank, retrievals, fixture_source_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=PROJECT_ROOT / "models/registry.yaml")
    parser.add_argument("--model-root", type=Path, default=Path("/models"))
    parser.add_argument("--receipt-root", type=Path, default=Path("/receipts"))
    parser.add_argument("--output-dir", type=Path, default=Path("/outputs"))
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.is_symlink():
        raise DoctorError("output directory must not be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise DoctorError("output directory must be empty")
    report, bank, retrievals, fixture_source_artifacts = run_doctor(
        registry=args.registry.resolve(),
        model_root=args.model_root.resolve(),
        receipt_root=args.receipt_root.resolve(),
    )
    files = {
        "bank.json": _json_bytes(bank),
        "fixture-source-artifacts.jsonl": _jsonl_bytes(fixture_source_artifacts),
        "retrievals.jsonl": _jsonl_bytes(retrievals),
        "report.json": _json_bytes(report),
    }
    for name, data in files.items():
        _write_once(output / name, data)
    manifest_unsigned = {
        "schema_version": 1,
        "status": STATUS,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "code_sha256s": {
            "harness/memory_trials/procedural_bank.py": _sha_path(
                PROJECT_ROOT / "harness/memory_trials/procedural_bank.py"
            ),
            "harness/memory_trials/dense_control.py": _sha_path(
                PROJECT_ROOT / "harness/memory_trials/dense_control.py"
            ),
            "scripts/dense_bge_factory.py": _sha_path(
                PROJECT_ROOT / "scripts/dense_bge_factory.py"
            ),
            "scripts/run_reasoningbank_frozen_bank_doctor.py": _sha_path(
                Path(__file__).resolve()
            ),
        },
        "model_receipt_file_sha256": _sha_path(
            args.receipt_root.resolve() / "bge-small-en-v1.5.json"
        ),
    }
    manifest = {
        **manifest_unsigned,
        "manifest_sha256": sha256_text(canonical_json(manifest_unsigned)),
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
