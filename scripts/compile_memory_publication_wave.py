#!/usr/bin/env python3
"""Compile one complete, non-cherry-pickable LongMemEval publication wave."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from harness.memory_trials.frozen import FrozenMemorySystem
from harness.memory_trials.schema import canonical_json, sha256_text
from harness.publication_attestation import verify_publication_claim_attestation
from scripts.compile_memory_public_docker_job import (
    CONTROL_SYSTEMS,
    DEFAULT_EXPERIMENT,
    compile_public_docker_manifest,
)
from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry
from scripts.freeze_memory_system_outputs import SYSTEM_IDENTITIES
from scripts.submit_docker_research_job import BATCH_SCRIPT, validate_manifest


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, owner: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {owner}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{owner} must be a JSON object")
    return payload


def _verify_root(payload: dict[str, Any], field: str, owner: str) -> str:
    unsigned = {key: value for key, value in payload.items() if key != field}
    actual = sha256_text(canonical_json(unsigned))
    if payload.get(field) != actual:
        raise ValueError(f"{owner} semantic root is invalid")
    return actual


def _experiment(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("publication experiment must be a schema-v1 mapping")
    source = payload.get("source")
    budget = payload.get("memory_budget")
    if not isinstance(source, dict) or not isinstance(budget, dict):
        raise ValueError("publication experiment lacks source or memory budget")
    if (
        source.get("type") != "longmemeval"
        or source.get("task_count") != 500
        or source.get("scientific_benchmark", {}).get("assignment") != "all-serve"
        or source.get("artifact_role") != "full-haystack-retrieval"
    ):
        raise ValueError("publication wave is restricted to full 500-task LongMemEval")
    return payload


def _matrix_controls(
    matrix_root: Path,
    matrix: dict[str, Any],
    experiment: dict[str, Any],
) -> list[dict[str, Any]]:
    if matrix.get("schema_version") != 1 or matrix.get("status") != ("FROZEN_CONTROL_MATRIX"):
        raise ValueError("publication control matrix is not frozen")
    source = matrix.get("task_source")
    contract = experiment["source"]
    budget = experiment["memory_budget"]
    if not isinstance(source, dict):
        raise ValueError("publication control matrix lacks task-source provenance")
    expected_source = {
        "dataset_revision": contract["dataset_revision"],
        "dataset_sha256": contract["dataset_sha256"],
        "dataset_size": contract["dataset_size"],
        "dataset_license": contract["dataset_license"],
        "adapter_version": contract["adapter_version"],
        "artifact_role": contract["artifact_role"],
        "candidate_seed": contract["candidate_seed"],
        "task_count": contract["task_count"],
        "task_selection": "all-tasks",
        "task_manifest_sha256": contract["full_task_manifest_sha256"],
    }
    for field, expected in expected_source.items():
        if source.get(field) != expected:
            raise ValueError(f"publication matrix source field {field} drifted")
    expected_budget = {
        "active_slots": budget["primary_active_slots"],
        "max_archive_reads": budget["max_archive_reads_per_opportunity"],
        "retrieval_top_k": budget["max_retrieval_top_k"],
        "max_injected_tokens": budget["max_injected_tokens"],
    }
    if source.get("budget") != expected_budget:
        raise ValueError("publication matrix memory budget drifted")
    if matrix.get("treatment_modes") != ["storage_and_service"]:
        raise ValueError("publication matrix treatment mode drifted")
    controls = matrix.get("controls")
    if not isinstance(controls, list) or not all(isinstance(control, dict) for control in controls):
        raise ValueError("publication matrix controls are invalid")
    control_ids = [control.get("control_id") for control in controls]
    if len(control_ids) != len(set(control_ids)) or set(control_ids) != set(CONTROL_SYSTEMS):
        raise ValueError("publication matrix must contain the complete registered roster")
    access_identified = int(matrix.get("event_kind_counts", {}).get("access", 0)) > 0
    expected_selection_count = int(contract["task_count"]) * 2
    for control in controls:
        control_id = str(control.get("control_id"))
        relative_value = control.get("bundle_path")
        if not isinstance(relative_value, str):
            raise ValueError("publication control lacks a bundle path")
        relative = Path(relative_value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("publication control bundle path is unsafe")
        bundle = (matrix_root / relative).resolve()
        if matrix_root not in bundle.parents or not bundle.is_file() or bundle.is_symlink():
            raise ValueError("publication control bundle is missing or escaped the matrix")
        frozen = FrozenMemorySystem(bundle)
        if control.get("bundle_sha256") != control.get("bundle_semantic_sha256"):
            raise ValueError(
                f"publication control {control.get('control_id')} semantic digest alias drifted"
            )
        if _sha256_file(bundle) != control.get("bundle_file_sha256"):
            raise ValueError(f"publication control {control.get('control_id')} digest drifted")
        if frozen.bundle_sha256 != control.get("bundle_semantic_sha256"):
            raise ValueError(f"publication control {control_id} semantic digest drifted")
        expected_system = SYSTEM_IDENTITIES[control_id]
        if (
            frozen.identity != expected_system
            or control.get("system_id") != expected_system
            or control.get("implementation_revision") != frozen.receipt.implementation_revision
        ):
            raise ValueError(f"publication control {control_id} system mapping drifted")
        if (
            frozen.metadata.get("selection_count") != expected_selection_count
            or control.get("selection_count") != expected_selection_count
        ):
            raise ValueError(f"publication control {control_id} task coverage drifted")
        expected_eligible = control_id != "reference" and (control_id != "lru" or access_identified)
        expected_reason = (
            "benchmark-has-no-explicit-access-events"
            if control_id == "lru" and not access_identified
            else "task-blind-hybrid-diagnostic-only"
            if control_id == "reference"
            else None
        )
        if (
            control.get("eligible_for_primary") is not expected_eligible
            or control.get("ineligibility_reason") != expected_reason
            or control.get("budget_class") != "matched"
        ):
            raise ValueError(f"publication control {control_id} eligibility drifted")
    eligible = [control for control in controls if control.get("eligible_for_primary") is True]
    if not eligible:
        raise ValueError("publication matrix has no primary-eligible controls")
    return sorted(eligible, key=lambda control: str(control["control_id"]))


def _write_file(path: Path, content: str) -> None:
    with path.open("xb", buffering=0) as handle:
        handle.write(content.encode())
        os.fsync(handle.fileno())


def preview_publication_wave(
    *,
    publication_capsule_path: Path,
    control_matrix_dir: Path,
    model_receipt_sha256: str,
    model_artifact_root: str,
    publication_trust_store_sha256: str,
    model_id: str = "qwen3.6-35b-a3b",
    experiment_path: Path = DEFAULT_EXPERIMENT,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    """Build the deterministic complete-wave document that an administrator signs."""

    capsule_path = publication_capsule_path.resolve(strict=True)
    matrix_root = control_matrix_dir.resolve(strict=True)
    matrix_path = matrix_root / "manifest.json"
    capsule = _load_json(capsule_path, "publication capsule")
    capsule_sha256 = _verify_root(capsule, "capsule_sha256", "publication capsule")
    if (
        capsule.get("schema_version") != 2
        or capsule.get("status") != "SEALED_PUBLICATION_CAPSULE_CANDIDATE"
        or capsule.get("publication_ready") is not False
    ):
        raise ValueError("publication capsule is not an attestation candidate")
    matrix = _load_json(matrix_path, "control matrix")
    matrix_sha256 = _verify_root(matrix, "matrix_sha256", "control matrix")
    experiment = _experiment(experiment_path)
    controls = _matrix_controls(matrix_root, matrix, experiment)
    registry = load_registry(registry_path)
    model_entry = registry["models"].get(model_id)
    if not isinstance(model_entry, dict):
        raise ValueError("publication model is absent from the reviewed registry")
    source = capsule.get("source")
    image = capsule.get("image")
    runtime = capsule.get("runtime")
    if not all(isinstance(value, dict) for value in (source, image, runtime)):
        raise ValueError("publication capsule lacks source, image, or runtime identity")
    batch_script_sha256 = _sha256_file(BATCH_SCRIPT)
    if runtime.get("batch_script_sha256") != batch_script_sha256:
        raise ValueError("publication capsule does not bind the active Slurm batch script")
    wave_contract = {
        "schema_version": 2,
        "scope": "longmemeval-500-all-serve-inactive-archive-retrieval",
        "publication_capsule_sha256": capsule_sha256,
        "publication_capsule_file_sha256": _sha256_file(capsule_path),
        "publication_trust_store_sha256": publication_trust_store_sha256,
        "control_matrix_sha256": matrix_sha256,
        "control_matrix_file_sha256": _sha256_file(matrix_path),
        "experiment_sha256": _sha256_file(experiment_path),
        "batch_script_sha256": batch_script_sha256,
        "model_id": model_id,
        "model_revision": model_entry["revision"],
        "model_receipt_sha256": model_receipt_sha256,
        "model_artifact_root_sha256": model_artifact_root,
        "registered_actor_contract": {
            "schema_version": 1,
            "model_id": model_id,
            "revision": model_entry["revision"],
            "artifact_root_sha256": model_artifact_root,
            "dtype": experiment["model"]["dtype"],
            "decoding": experiment["model"]["decoding"],
            "prompt_protocol": "replayable-memory-world-v1",
            "response_schema": "answer-or-tool-json-v1",
            "deterministic_algorithms": True,
            "attention_implementation": "eager",
            "memory_budget_profile": "matched",
        },
        "command_schema": "longmemeval-publication-actor-all-serve-v2",
        "task_manifest_sha256": experiment["source"]["full_task_manifest_sha256"],
        "eligible_controls": [
            {
                "control_id": control["control_id"],
                "system_id": control["system_id"],
                "bundle_semantic_sha256": control["bundle_semantic_sha256"],
                "bundle_file_sha256": control["bundle_file_sha256"],
            }
            for control in controls
        ],
    }
    wave_sha256 = sha256_text(canonical_json(wave_contract))
    return {**wave_contract, "wave_sha256": wave_sha256}


def compile_publication_wave(
    *,
    publication_capsule_path: Path,
    publication_attestation_path: Path,
    publication_trust_store_path: Path,
    publication_trust_store_sha256: str,
    control_matrix_dir: Path,
    output_dir: Path,
    run_root: str,
    model_cache_host: str,
    model_receipt_sha256: str,
    model_artifact_root: str,
    public_benchmark_path: str,
    model_id: str = "qwen3.6-35b-a3b",
    experiment_path: Path = DEFAULT_EXPERIMENT,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    """Compile every primary-eligible control from one sealed matrix."""

    capsule_path = publication_capsule_path.resolve(strict=True)
    attestation_path = publication_attestation_path.resolve(strict=True)
    trust_store_path = publication_trust_store_path.resolve(strict=True)
    matrix_root = control_matrix_dir.resolve(strict=True)
    matrix_path = matrix_root / "manifest.json"
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite publication wave: {output_dir}")
    wave_document = preview_publication_wave(
        publication_capsule_path=capsule_path,
        control_matrix_dir=matrix_root,
        model_receipt_sha256=model_receipt_sha256,
        model_artifact_root=model_artifact_root,
        publication_trust_store_sha256=publication_trust_store_sha256,
        model_id=model_id,
        experiment_path=experiment_path,
        registry_path=registry_path,
    )
    wave_sha256 = str(wave_document["wave_sha256"])
    wave_contract = {key: value for key, value in wave_document.items() if key != "wave_sha256"}
    wave_rendered = json.dumps(wave_document, indent=2, sort_keys=True) + "\n"
    wave_file_sha256 = hashlib.sha256(wave_rendered.encode()).hexdigest()
    attestation_receipt = verify_publication_claim_attestation(
        capsule_path=capsule_path,
        matrix_path=matrix_path,
        experiment_path=experiment_path,
        wave=wave_document,
        batch_script_path=BATCH_SCRIPT,
        attestation_path=attestation_path,
        trust_store_path=trust_store_path,
        expected_trust_store_sha256=publication_trust_store_sha256,
    )
    capsule = _load_json(capsule_path, "publication capsule")
    capsule_sha256 = str(wave_contract["publication_capsule_sha256"])
    matrix = _load_json(matrix_path, "control matrix")
    matrix_sha256 = str(wave_contract["control_matrix_sha256"])
    experiment = _experiment(experiment_path)
    controls = _matrix_controls(matrix_root, matrix, experiment)
    source = capsule.get("source")
    image = capsule.get("image")
    if not isinstance(source, dict) or not isinstance(image, dict):
        raise ValueError("publication capsule lacks source or image identity")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        _write_file(staging / "wave-contract.json", wave_rendered)
        manifest_rows: list[dict[str, Any]] = []
        for control in controls:
            bundle_path = (matrix_root / control["bundle_path"]).resolve()
            raw = compile_public_docker_manifest(
                stage="actor-all-serve",
                image_id=image["image_id"],
                run_root=run_root,
                git_sha=source["git_sha"],
                source_sha256=source["archive_sha256"],
                model_cache_host=model_cache_host,
                model_receipt_sha256=model_receipt_sha256,
                model_artifact_root=model_artifact_root,
                public_benchmark_path=public_benchmark_path,
                model_id=model_id,
                memory_bundle_path=str(bundle_path),
                memory_bundle_sha256=control["bundle_file_sha256"],
                memory_control_id=control["control_id"],
                experiment_path=experiment_path,
                registry_path=registry_path,
            )
            raw["command"].extend(
                [
                    "--publication-capsule",
                    "/inputs/publication-capsule.json",
                    "--publication-capsule-attestation",
                    "/inputs/publication-capsule-attestation.json",
                    "--publication-trust-store",
                    "/etc/cotcodec/trust/publication-attestors.json",
                    "--expected-publication-trust-sha256",
                    publication_trust_store_sha256,
                    "--control-matrix-manifest",
                    "/inputs/control-matrix-manifest.json",
                    "--publication-wave-contract",
                    "/inputs/publication-wave-contract.json",
                    "--expected-wave-sha256",
                    wave_sha256,
                    "--expected-control-id",
                    control["control_id"],
                    "--expected-system-id",
                    control["system_id"],
                ]
            )
            raw["claim_admission"] = {
                "publication_capsule": {
                    "host_path": str(capsule_path),
                    "file_sha256": wave_contract["publication_capsule_file_sha256"],
                    "capsule_sha256": capsule_sha256,
                    "image_id": image["image_id"],
                    "git_sha": source["git_sha"],
                    "source_sha256": source["archive_sha256"],
                },
                "publication_attestation": {
                    "host_path": str(attestation_path),
                    "file_sha256": attestation_receipt["attestation_file_sha256"],
                    "trust_store_host_path": str(trust_store_path),
                    "trust_store_sha256": attestation_receipt["trust_store_sha256"],
                    "key_id": attestation_receipt["key_id"],
                },
                "control_matrix": {
                    "host_path": str(matrix_path),
                    "file_sha256": wave_contract["control_matrix_file_sha256"],
                    "matrix_sha256": matrix_sha256,
                    "task_manifest_sha256": wave_contract["task_manifest_sha256"],
                },
                "wave": {
                    "host_path": str(output_dir / "wave-contract.json"),
                    "file_sha256": wave_file_sha256,
                    "wave_sha256": wave_sha256,
                    "control_id": control["control_id"],
                    "system_id": control["system_id"],
                    "eligible_for_primary": True,
                    "bundle_semantic_sha256": control["bundle_semantic_sha256"],
                    "bundle_file_sha256": control["bundle_file_sha256"],
                },
            }
            validate_manifest(raw, verify_claim_files=False)
            filename = f"{control['control_id']}.yaml"
            rendered = yaml.safe_dump(raw, sort_keys=False)
            _write_file(staging / filename, rendered)
            manifest_rows.append(
                {
                    "control_id": control["control_id"],
                    "system_id": control["system_id"],
                    "bundle_semantic_sha256": control["bundle_semantic_sha256"],
                    "bundle_file_sha256": control["bundle_file_sha256"],
                    "manifest": filename,
                    "manifest_sha256": sha256_text(rendered),
                }
            )
        index_unsigned = {
            "schema_version": 1,
            "status": "COMPILED_PUBLICATION_WAVE",
            "scientific_result": False,
            "reason": "Admission manifests only; no model or benchmark result.",
            "wave_sha256": wave_sha256,
            "wave_contract": wave_contract,
            "publication_claim_attestation": attestation_receipt,
            "cells": manifest_rows,
        }
        index = {
            **index_unsigned,
            "index_sha256": sha256_text(canonical_json(index_unsigned)),
        }
        _write_file(
            staging / "index.json",
            json.dumps(index, indent=2, sort_keys=True) + "\n",
        )
        os.rename(staging, output_dir)
        descriptor = os.open(output_dir.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return index
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publication-capsule", type=Path, required=True)
    parser.add_argument("--publication-attestation", type=Path, required=True)
    parser.add_argument("--publication-trust-store", type=Path, required=True)
    parser.add_argument("--publication-trust-store-sha256", required=True)
    parser.add_argument("--control-matrix-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--model-cache-host", required=True)
    parser.add_argument("--model-receipt-sha256", required=True)
    parser.add_argument("--model-artifact-root", required=True)
    parser.add_argument("--public-benchmark-path", required=True)
    parser.add_argument("--model-id", default="qwen3.6-35b-a3b")
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    try:
        index = compile_publication_wave(
            publication_capsule_path=args.publication_capsule,
            publication_attestation_path=args.publication_attestation,
            publication_trust_store_path=args.publication_trust_store,
            publication_trust_store_sha256=args.publication_trust_store_sha256,
            control_matrix_dir=args.control_matrix_dir,
            output_dir=args.output_dir,
            run_root=args.run_root,
            model_cache_host=args.model_cache_host,
            model_receipt_sha256=args.model_receipt_sha256,
            model_artifact_root=args.model_artifact_root,
            public_benchmark_path=args.public_benchmark_path,
            model_id=args.model_id,
            experiment_path=args.experiment,
            registry_path=args.registry,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(index, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
