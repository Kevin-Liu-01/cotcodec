#!/usr/bin/env python3
"""Validate the retained MemForge fresh-install negative evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_STATUS = "MEMFORGE_FRESH_INSTALL_ADMISSION_KILLED"
EXPECTED_REVISION = "16e2f15c5881a38911f64ca81b3dc0b25d6207ec"
EXPECTED_TREE = "97411a5c0318c3f4b1d273ab0696b915184fca3a"
EXPECTED_IMAGES = {
    "official-compose-postgres": {
        "ref": (
            "postgres@sha256:"
            "cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
        ),
        "id": (
            "sha256:"
            "cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
        ),
        "markers": (
            'extension "vector" is not available',
            "/usr/local/share/postgresql/extension/vector.control",
            "schema.sql:14",
        ),
    },
    "pgvector-enabled-control": {
        "ref": (
            "pgvector/pgvector@sha256:"
            "ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
        ),
        "id": (
            "sha256:"
            "ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
        ),
        "markers": (
            'relation "warm_tier" does not exist',
            "schema.sql:57",
        ),
    },
}
EXPECTED_BOUNDARY = {
    "hot_warm_cold_lifecycle_evaluated": False,
    "graph_quality_evaluated": False,
    "memory_quality_evaluated": False,
    "repair_arm_evaluated": False,
}


class MemForgeEvidenceError(ValueError):
    """Raised when retained MemForge evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemForgeEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MemForgeEvidenceError(f"{owner}: expected object")
    return payload


def _validate_lane(
    payload: dict[str, Any], *, lane: str, repeat: int, logs: bytes
) -> None:
    expected = EXPECTED_IMAGES[lane]
    argv = payload.get("runtime_argv")
    if (
        payload.get("schema_version") != 1
        or payload.get("source_revision") != EXPECTED_REVISION
        or payload.get("repeat") != repeat
        or payload.get("lane") != lane
        or payload.get("status") != EXPECTED_STATUS
        or payload.get("exit_code") != 3
        or payload.get("logs_sha256") != _sha(logs)
        or payload.get("checks")
        != {
            "all_failure_markers_present": True,
            "fresh_install_never_completed": True,
            "registered_nonzero_exit": True,
        }
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("h100_actor_admission") is not False
        or not isinstance(argv, list)
        or "--network" not in argv
        or argv[argv.index("--network") + 1] != "none"
        or "--read-only" not in argv
        or argv[argv.index("--cap-drop") + 1] != "ALL"
        or "no-new-privileges" not in argv
        or "--gpus" in argv
        or "sudo" in argv
        or argv[-1] != expected["ref"]
    ):
        raise MemForgeEvidenceError(f"lane receipt drifted: repeat {repeat} {lane}")
    decoded = logs.decode(errors="replace")
    if not all(marker in decoded for marker in expected["markers"]):
        raise MemForgeEvidenceError(f"lane failure markers drifted: {lane}")


def validate_memforge_fresh_install_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "MemForge evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise MemForgeEvidenceError("project_root is required")
        root = project_root

    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "memforge"
        or bundle.get("source_revisions")
        != {"https://github.com/salishforge/memforge": EXPECTED_REVISION}
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("run_count") != 2
        or bundle.get("claim_boundary") != EXPECTED_BOUNDARY
    ):
        raise MemForgeEvidenceError("evidence identity drifted")

    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise MemForgeEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected:
            raise MemForgeEvidenceError(f"code receipt drifted: {name}")

    artifact_root = root / bundle.get("artifact_root", "")
    receipts = bundle.get("artifact_files")
    if artifact_root.is_symlink() or not artifact_root.is_dir() or not isinstance(receipts, dict):
        raise MemForgeEvidenceError("artifact root or roster is invalid")
    if set(receipts) != {
        "experiment.yaml",
        "image-inspect-official-compose-postgres.json",
        "image-inspect-pgvector-enabled-control.json",
        "manifest.json",
        "repeat-1-official-compose-postgres.json",
        "repeat-1-official-compose-postgres.log",
        "repeat-1-pgvector-enabled-control.json",
        "repeat-1-pgvector-enabled-control.log",
        "repeat-2-official-compose-postgres.json",
        "repeat-2-official-compose-postgres.log",
        "repeat-2-pgvector-enabled-control.json",
        "repeat-2-pgvector-enabled-control.log",
        "report.json",
        "schema.sql",
        "source-receipt.json",
        "source.tar",
    }:
        raise MemForgeEvidenceError("artifact roster drifted")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = artifact_root / name
        if path.is_symlink() or not path.is_file():
            raise MemForgeEvidenceError(f"artifact missing: {name}")
        files[name] = path.read_bytes()
        if _sha(files[name]) != expected:
            raise MemForgeEvidenceError(f"artifact drifted: {name}")

    for repeat in (1, 2):
        for lane in EXPECTED_IMAGES:
            prefix = f"repeat-{repeat}-{lane}"
            _validate_lane(
                _object(files[f"{prefix}.json"], prefix),
                lane=lane,
                repeat=repeat,
                logs=files[f"{prefix}.log"],
            )

    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("source_revision") != EXPECTED_REVISION
        or report.get("source_tree") != EXPECTED_TREE
        or report.get("run_count") != 2
        or report.get("lane_count") != 4
        or report.get("findings")
        != {
            "canonical_schema_references_warm_tier_before_creation": True,
            "exact_revision_lifecycle_not_executable": True,
            "official_compose_image_lacks_vector_extension": True,
        }
        or report.get("claim_boundary") != EXPECTED_BOUNDARY
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
    ):
        raise MemForgeEvidenceError("summary semantics drifted")

    for lane, expected in EXPECTED_IMAGES.items():
        rows = json.loads(files[f"image-inspect-{lane}.json"])
        image = rows[0] if isinstance(rows, list) and len(rows) == 1 else {}
        if (
            image.get("Id") != expected["id"]
            or image.get("Architecture") != "arm64"
            or image.get("Os") != "linux"
            or expected["ref"] not in (image.get("RepoDigests") or [])
            or image.get("Config", {}).get("Entrypoint") != ["docker-entrypoint.sh"]
            or image.get("Config", {}).get("Cmd") != ["postgres"]
        ):
            raise MemForgeEvidenceError(f"image provenance drifted: {lane}")

    source = _object(files["source-receipt.json"], "source receipt")
    if (
        source.get("git_sha") != EXPECTED_REVISION
        or source.get("git_tree") != EXPECTED_TREE
        or source.get("archive_sha256") != _sha(files["source.tar"])
        or source.get("license_sha256")
        != "dac7f81d95c038f342d1afd54d48527ac370ed03bb20b008dfefb68f1d6fd6b3"
        or source.get("package_lock_sha256")
        != "15c4f6a7e24ea93042b608143eae9c698dca7ccf57180f2d18e1309cb8cc32c9"
        or source.get("canonical_schema_sha256") != _sha(files["schema.sql"])
    ):
        raise MemForgeEvidenceError("source receipt drifted")
    schema_lines = files["schema.sql"].decode().splitlines()
    if (
        schema_lines[13] != "CREATE EXTENSION IF NOT EXISTS vector;"
        or "ON warm_tier" not in schema_lines[56]
        or schema_lines[72] != "CREATE TABLE IF NOT EXISTS warm_tier ("
    ):
        raise MemForgeEvidenceError("canonical schema ordering drifted")

    manifest = _object(files["manifest.json"], "manifest")
    expected_files = {
        name: digest for name, digest in receipts.items() if name != "manifest.json"
    }
    if (
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_files)
        or manifest.get("files") != expected_files
    ):
        raise MemForgeEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence = validate_memforge_fresh_install_evidence(
        root / "research/evidence/memory/memforge-fresh-install-negative-v1.json",
        project_root=root,
    )
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
