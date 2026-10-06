#!/usr/bin/env python3
"""Download, verify, and seal immutable public memory-benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    LONGMEMEVAL_DATASET_ID,
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_LICENSE,
    LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
    LONGMEMEVAL_ORACLE_FILENAME,
    LONGMEMEVAL_ORACLE_SHA256,
    LONGMEMEVAL_ORACLE_SIZE,
    LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    LONGMEMEVAL_S_FILENAME,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
    LongMemEvalTaskSource,
    longmemeval_download_url,
    task_manifest_sha256,
)
from harness.memory_trials.public_sources import sha256_file  # noqa: E402
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402

DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "benchmarks"


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_file(path: Path, *, expected_size: int, expected_sha256: str) -> None:
    if not path.is_file():
        raise ValueError(f"benchmark artifact is missing: {path}")
    size = path.stat().st_size
    if size != expected_size:
        raise ValueError(f"benchmark artifact size mismatch: {size} != {expected_size}")
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise ValueError(f"benchmark artifact digest mismatch: {digest}")


def _download_once(
    destination: Path,
    *,
    url: str,
    expected_size: int,
    expected_sha256: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        _verify_file(
            destination,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        return
    temporary = destination.with_name(f".{destination.name}.part-{os.getpid()}")
    if temporary.exists():
        raise ValueError(f"refusing to reuse stale partial download: {temporary}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "cotcodec-memory-benchmark-preparer/1.0"},
    )
    try:
        with (
            urllib.request.urlopen(request, timeout=120) as response,  # noqa: S310
            temporary.open("xb", buffering=0) as handle,
        ):
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
            os.fsync(handle.fileno())
        _verify_file(
            temporary,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def compile_longmemeval_manifest(
    dataset_path: Path,
    *,
    expected_sha256: str = LONGMEMEVAL_ORACLE_SHA256,
    expected_size: int = LONGMEMEVAL_ORACLE_SIZE,
    dataset_revision: str = LONGMEMEVAL_DATASET_REVISION,
    artifact_role: str = LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
) -> dict[str, Any]:
    source = LongMemEvalTaskSource(
        dataset_path,
        expected_sha256=expected_sha256,
        expected_size=expected_size,
        dataset_revision=dataset_revision,
        artifact_role=artifact_role,
    )
    tasks = tuple(source.load(task_id) for task_id in source.ids())
    strata = Counter(task.stratum.value for task in tasks)
    groups = Counter(task.group_id for task in tasks)
    unsigned = {
        "schema_version": 2,
        "status": "VERIFIED_PUBLIC_BENCHMARK",
        "scientific_result": False,
        "reason": (
            "Immutable source and task-conversion receipt only; no memory-system "
            "or model-quality claim."
        ),
        "source": dict(source.provenance),
        "artifact": {
            "path": str(dataset_path.resolve()),
            "sha256": expected_sha256,
            "size": expected_size,
            "download_url": longmemeval_download_url(
                revision=dataset_revision,
                filename=dataset_path.name,
            ),
        },
        "adapter_version": source.provenance["adapter_version"],
        "artifact_role": source.provenance["artifact_role"],
        "task_manifest_sha256": task_manifest_sha256(source),
        "task_count": len(tasks),
        "group_count": len(groups),
        "duplicate_group_count": sum(count > 1 for count in groups.values()),
        "strata": dict(sorted(strata.items())),
        "candidate_policy_audit": {
            "policy": source.provenance["candidate_policy"],
            "forbidden_inputs": source.provenance["candidate_forbidden_inputs"],
            "exactly_one_candidate_per_task": all(
                sum(event.candidate for event in task.events) == 1 for task in tasks
            ),
            "all_candidates_precede_query": all(
                task.write_step < task.eligibility_step for task in tasks
            ),
        },
    }
    if source.provenance["artifact_role"] == LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE:
        unsigned["transport_panel"] = (
            source.transport_panel_receipt()
            if source.provenance["raw_rows"] == 500
            else {
                "status": "NOT_DERIVED_FROM_TEST_FIXTURE",
                "scientific_result": False,
            }
        )
    return {**unsigned, "manifest_sha256": sha256_text(canonical_json(unsigned))}


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError(f"refusing to overwrite a different manifest: {path}")
        return
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def prepare_longmemeval(
    output_root: Path,
    *,
    artifact_role: str = LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
    verify_only: bool,
) -> dict[str, Any]:
    if artifact_role == LONGMEMEVAL_ORACLE_ARTIFACT_ROLE:
        filename = LONGMEMEVAL_ORACLE_FILENAME
        expected_sha256 = LONGMEMEVAL_ORACLE_SHA256
        expected_size = LONGMEMEVAL_ORACLE_SIZE
        manifest_name = "manifest-oracle-context-v2.json"
    elif artifact_role == LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE:
        filename = LONGMEMEVAL_S_FILENAME
        expected_sha256 = LONGMEMEVAL_S_SHA256
        expected_size = LONGMEMEVAL_S_SIZE
        manifest_name = "manifest-full-haystack-retrieval-v2.json"
    else:
        raise ValueError(f"unsupported LongMemEval artifact role: {artifact_role}")
    dataset_dir = output_root / "longmemeval" / LONGMEMEVAL_DATASET_REVISION
    dataset_path = dataset_dir / filename
    if verify_only:
        _verify_file(
            dataset_path,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
    else:
        _download_once(
            dataset_path,
            url=longmemeval_download_url(filename=filename),
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
    manifest = compile_longmemeval_manifest(
        dataset_path,
        expected_sha256=expected_sha256,
        expected_size=expected_size,
        artifact_role=artifact_role,
    )
    _write_manifest(dataset_dir / manifest_name, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "benchmark",
        choices=("longmemeval-oracle", "longmemeval-s"),
        help=(
            f"Pinned {LONGMEMEVAL_DATASET_ID}@{LONGMEMEVAL_DATASET_REVISION} "
            f"({LONGMEMEVAL_LICENSE})"
        ),
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    artifact_role = (
        LONGMEMEVAL_ORACLE_ARTIFACT_ROLE
        if args.benchmark == "longmemeval-oracle"
        else LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE
    )
    manifest = prepare_longmemeval(
        args.output_root.resolve(),
        artifact_role=artifact_role,
        verify_only=args.verify_only,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
