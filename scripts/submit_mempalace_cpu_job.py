#!/usr/bin/env python3
"""Validate and submit the fixed offline MemPalace CPU reproduction workload."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.public_sources import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
)
from scripts.run_mempalace_upstream_reproduction import (  # noqa: E402
    ReproductionExpectations,
    _load_runtime_receipt,
)
from scripts.seal_publication_capsule import _sbom_contract  # noqa: E402

BATCH_SCRIPT = PROJECT_ROOT / "infra/slurm/host-single-node/mempalace-cpu.sbatch"
RUNTIME = "docker-cpu-mempalace-reproduction-v1"
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
SHA_RE = re.compile(r"[0-9a-f]{64}")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
JOB_ID_RE = re.compile(r"[1-9][0-9]{0,19}")
PATH_RE = re.compile(r"/[A-Za-z0-9._/-]{1,511}")
IMAGE_REFERENCE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)
MAX_CPU_HOURS = 512.0


@dataclass(frozen=True)
class CpuJobExpectations:
    dataset_sha256: str = LONGMEMEVAL_S_SHA256
    dataset_size: int = LONGMEMEVAL_S_SIZE
    dataset_revision: str = LONGMEMEVAL_DATASET_REVISION


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or PATH_RE.fullmatch(value) is None
        or ".." in Path(value).parts
    ):
        raise ValueError(f"{field} must be one simple absolute path")
    return value


def _integer(mapping: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = mapping.get(key)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{key} must be an integer in [{minimum}, {maximum}]")
    return value


def _finite_number(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{key} must be finite and positive")
    return number


def _verified_file(path_value: Any, sha_value: Any, field: str) -> tuple[str, str]:
    path = Path(_safe_path(path_value, f"{field}.host_path"))
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{field} must be a regular non-symlink file")
    if not isinstance(sha_value, str) or SHA_RE.fullmatch(sha_value) is None:
        raise ValueError(f"{field}.sha256 must be lowercase 64-hex")
    if _sha256_file(path) != sha_value:
        raise ValueError(f"{field} digest mismatch")
    return str(path), sha_value


def validate_manifest(
    raw: dict[str, Any],
    *,
    expectations: CpuJobExpectations | None = None,
) -> dict[str, Any]:
    expectations = expectations or CpuJobExpectations()
    if raw.get("schema_version") != 1 or raw.get("runtime") != RUNTIME:
        raise ValueError("manifest schema_version or runtime is unsupported")
    name = raw.get("name")
    study_id = raw.get("study_id")
    if not isinstance(name, str) or NAME_RE.fullmatch(name) is None:
        raise ValueError("name must be a safe lowercase job name")
    if not isinstance(study_id, str) or NAME_RE.fullmatch(study_id) is None:
        raise ValueError("study_id must be a safe lowercase identifier")

    image = raw.get("image")
    if not isinstance(image, dict):
        raise ValueError("image must be an object")
    image_id = image.get("id")
    repo_digest = image.get("repo_digest")
    base_reference = image.get("cotcodec_base_image_reference")
    minilm_root = image.get("minilm_artifact_root_sha256")
    if not isinstance(image_id, str) or IMAGE_ID_RE.fullmatch(image_id) is None:
        raise ValueError("image.id must be one exact local sha256 image ID")
    if not isinstance(minilm_root, str) or SHA_RE.fullmatch(minilm_root) is None:
        raise ValueError("image.minilm_artifact_root_sha256 must be lowercase 64-hex")
    if not isinstance(repo_digest, str) or IMAGE_REFERENCE_RE.fullmatch(repo_digest) is None:
        raise ValueError("image.repo_digest must be immutable")
    if (
        not isinstance(base_reference, str)
        or IMAGE_REFERENCE_RE.fullmatch(base_reference) is None
    ):
        raise ValueError("image.cotcodec_base_image_reference must be immutable")
    sbom_input = image.get("sbom")
    if not isinstance(sbom_input, dict):
        raise ValueError("image.sbom must be an object")
    sbom_path, sbom_sha256 = _verified_file(
        sbom_input.get("host_path"), sbom_input.get("sha256"), "image.sbom"
    )
    sbom_contract = _sbom_contract(Path(sbom_path), image_id, [repo_digest])
    if sbom_contract["sha256"] != sbom_sha256:
        raise ValueError("image SBOM changed during semantic validation")

    dataset = raw.get("dataset")
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be an object")
    dataset_path, dataset_sha256 = _verified_file(
        dataset.get("host_path"), dataset.get("sha256"), "dataset"
    )
    dataset_size = Path(dataset_path).stat().st_size
    if (
        dataset_sha256 != expectations.dataset_sha256
        or dataset_size != expectations.dataset_size
        or dataset.get("revision") != expectations.dataset_revision
    ):
        raise ValueError("dataset differs from the registered LongMemEval artifact")

    runtime_input = raw.get("runtime_receipt")
    if not isinstance(runtime_input, dict):
        raise ValueError("runtime_receipt must be an object")
    runtime_path, runtime_sha256 = _verified_file(
        runtime_input.get("host_path"),
        runtime_input.get("sha256"),
        "runtime_receipt",
    )
    receipt, computed_runtime_sha256 = _load_runtime_receipt(
        Path(runtime_path), ReproductionExpectations()
    )
    if computed_runtime_sha256 != runtime_sha256:
        raise ValueError("runtime receipt digest changed during validation")
    expected_receipt_bindings = {
        "image_id": image_id,
        "image_repo_digest": repo_digest,
        "image_sbom_sha256": sbom_sha256,
        "cotcodec_base_image_reference": base_reference,
        "embedding_artifact_root_sha256": minilm_root,
    }
    for field, value in expected_receipt_bindings.items():
        if receipt.get(field) != value:
            raise ValueError(f"runtime receipt field {field!r} differs from image")

    resources = raw.get("resources")
    budget = raw.get("budget")
    if not isinstance(resources, dict) or not isinstance(budget, dict):
        raise ValueError("resources and budget must be objects")
    cpus = _integer(resources, "cpus", 1, 64)
    memory_gb = _integer(resources, "memory_gb", 8, 256)
    minutes = _integer(resources, "minutes", 10, 1440)
    max_cpu_hours = _finite_number(budget, "max_cpu_hours")
    max_wall_minutes = _integer(budget, "max_wall_minutes", 10, 1440)
    if max_cpu_hours > MAX_CPU_HOURS:
        raise ValueError(f"max_cpu_hours exceeds the hard ceiling {MAX_CPU_HOURS}")
    if cpus * minutes / 60 > max_cpu_hours:
        raise ValueError("requested CPU allocation exceeds max_cpu_hours")
    if max_wall_minutes != minutes:
        raise ValueError("budget.max_wall_minutes must equal resources.minutes")

    run_root = _safe_path(raw.get("run_root"), "run_root")
    run_root_path = Path(run_root)
    if not run_root_path.is_dir() or run_root_path.is_symlink():
        raise ValueError("run_root must be a regular existing directory")
    predecessor = raw.get("resume_from_job_id")
    if predecessor is not None and (
        not isinstance(predecessor, str) or JOB_ID_RE.fullmatch(predecessor) is None
    ):
        raise ValueError("resume_from_job_id must be a Slurm job ID")

    return {
        "schema_version": 1,
        "runtime": RUNTIME,
        "name": name,
        "study_id": study_id,
        "image": {
            "id": image_id,
            "repo_digest": repo_digest,
            "sbom": {
                "host_path": sbom_path,
                "sha256": sbom_sha256,
                "format": sbom_contract["format"],
                "scanner_version": sbom_contract["scan"]["scanner_version"],
            },
            "cotcodec_base_image_reference": base_reference,
            "minilm_artifact_root_sha256": minilm_root,
        },
        "dataset": {
            "host_path": dataset_path,
            "sha256": dataset_sha256,
            "size_bytes": dataset_size,
            "revision": expectations.dataset_revision,
        },
        "runtime_receipt": {
            "host_path": runtime_path,
            "sha256": runtime_sha256,
        },
        "resources": {"cpus": cpus, "memory_gb": memory_gb, "minutes": minutes},
        "budget": {
            "max_cpu_hours": max_cpu_hours,
            "max_wall_minutes": minutes,
        },
        "run_root": run_root,
        "resume_from_job_id": predecessor,
        "batch_script_sha256": _sha256_file(BATCH_SCRIPT),
        "network_policy": "none",
        "gpu_count": 0,
        "scientific_result": False,
    }


def sbatch_argv(manifest: dict[str, Any], *, test_only: bool) -> list[str]:
    resources = manifest["resources"]
    hours, minutes = divmod(resources["minutes"], 60)
    manifest_hex = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode().hex()
    exported = {
        "COTCODEC_MEMPALACE_MANIFEST_HEX": manifest_hex,
        "COTCODEC_IMAGE_ID": manifest["image"]["id"],
        "COTCODEC_IMAGE_REPO_DIGEST_HEX": manifest["image"]["repo_digest"]
        .encode()
        .hex(),
        "COTCODEC_IMAGE_SBOM_HOST_HEX": manifest["image"]["sbom"]["host_path"]
        .encode()
        .hex(),
        "COTCODEC_IMAGE_SBOM_SHA256": manifest["image"]["sbom"]["sha256"],
        "COTCODEC_BASE_IMAGE_REF_HEX": manifest["image"][
            "cotcodec_base_image_reference"
        ].encode().hex(),
        "COTCODEC_MINILM_ROOT": manifest["image"]["minilm_artifact_root_sha256"],
        "COTCODEC_DATASET_HOST_HEX": manifest["dataset"]["host_path"].encode().hex(),
        "COTCODEC_DATASET_SHA256": manifest["dataset"]["sha256"],
        "COTCODEC_DATASET_SIZE": str(manifest["dataset"]["size_bytes"]),
        "COTCODEC_RUNTIME_RECEIPT_HOST_HEX": manifest["runtime_receipt"][
            "host_path"
        ].encode().hex(),
        "COTCODEC_RUNTIME_RECEIPT_SHA256": manifest["runtime_receipt"]["sha256"],
        "COTCODEC_RUN_ROOT_HEX": manifest["run_root"].encode().hex(),
        "COTCODEC_STUDY_ID": manifest["study_id"],
        "COTCODEC_BATCH_SHA256": manifest["batch_script_sha256"],
    }
    if predecessor := manifest.get("resume_from_job_id"):
        exported["COTCODEC_PREDECESSOR_JOB_ID"] = predecessor
    export_argument = ",".join(f"{key}={value}" for key, value in exported.items())
    argv = [
        "sbatch",
        "--parsable",
        "--partition=research",
        "--nodes=1",
        "--ntasks=1",
        f"--job-name={manifest['name']}",
        f"--cpus-per-task={resources['cpus']}",
        f"--mem={resources['memory_gb']}G",
        f"--time={hours:02d}:{minutes:02d}:00",
        "--signal=B:USR1@180",
        f"--chdir={manifest['run_root']}",
        f"--output={manifest['run_root']}/slurm-%j.out",
        f"--export={export_argument}",
    ]
    if test_only:
        argv.append("--test-only")
    argv.append(str(BATCH_SCRIPT))
    return argv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-only", action="store_true")
    args = parser.parse_args()
    try:
        raw = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        parser.error(f"cannot load manifest: {exc}")
    if not isinstance(raw, dict):
        parser.error("manifest must contain one YAML object")
    try:
        manifest = validate_manifest(raw)
    except ValueError as exc:
        parser.error(str(exc))
    argv = sbatch_argv(manifest, test_only=args.test_only)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "runtime": RUNTIME,
                    "gpu_count": 0,
                    "cpu_hours": (
                        manifest["resources"]["cpus"]
                        * manifest["resources"]["minutes"]
                        / 60
                    ),
                    "argv": argv,
                },
                indent=2,
            )
        )
        return 0
    completed = subprocess.run(argv, check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        parser.exit(completed.returncode, f"sbatch failed: {detail}\n")
    print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
