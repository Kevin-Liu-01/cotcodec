#!/usr/bin/env python3
"""Seal ignored local memory results into tracked, self-contained evidence JSON."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import math
import os
import random
import re
import sys
import tempfile
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TOTAL_STATUS = "BLOCKED_NATIVE_RESTART_DEFECT_REPRODUCED"
TOTAL_REVISION = "a2630f671be9b12df8b8ac78df9d26f7053d2fa9"
ALLMEM_REVISION = "f5d6912717b0d6c65a19ba2660fb9b6637d4d50e"
ALLMEM_STATUS = "BLOCKED_SPLIT_MERGE_RAW_EVIDENCE_RECOVERY"
ALLMEM_EXPERIMENT_SHA256 = (
    "48eb77c3791fdc0ca816e30daeb66e1c164a79f32c1571c29518d984d87e7c66"
)
ALLMEM_DOCKERFILE_SHA256 = (
    "1854958cae253985c2a890cdd2c4ed3efe0eef4f3ebbbaacc882ba51130d8e10"
)
ALLMEM_DOCTOR_SHA256 = (
    "3caf6c5590f557d7e55f4322c13b0f01a7b895ec83f252178261d32ee9a76598"
)
ALLMEM_RUNNER_SHA256 = (
    "1f188a8524232fa2553aaba5b4ed48e4410617a727d29ee773f72aec5db49113"
)
ALLMEM_VALIDATOR_SHA256 = (
    "b3ad52c240ef0351bc886b098715d6c4982a0892f0a8523ec1ef5af25fef6f18"
)
HERMES_REVISION = "a90d5369f76c87c98547d2e283aa26d5cfabf322"
MEMORI_REVISION = "538b61f245295aa1a43df8033879f8293627f74d"
NEO4J_REVISION = "231d60eac9401ab156ba194b519d89dd644dadb8"
NEO4J_STATUS = "NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS"
HIPPO_REVISION = "4aeb04c68ff079ff1713c977ac4d2a96757cff44"
HIPPO_STATUS = "BLOCKED_CROSS_TENANT_CONSOLIDATION_AND_PURGE_RESIDUE_REPRODUCED"
HIPPO_EXPERIMENT_SHA256 = "5ea9c0b30a720ebadd4e473a5d0273a8829fa0ac7c98f830cb8df48d055e6799"
HIPPO_DOCKERFILE_SHA256 = "4da559c21db5385d1cf724741938768d00dca4cb12659af81356b1f0d5a01b64"
HIPPO_DOCTOR_SHA256 = "633c22e232dc8db55af8c0c0a242fc388d8a9e7683e34ee644d21a9e1d84d9a8"
MAGIC_CONTEXT_REVISION = "13e1d4c3fa3803ba1f4595029d8c4750dc9bef98"
MAGIC_CONTEXT_STATUS = "BLOCKED_PORTABLE_LIFECYCLE_AND_SECURE_PURGE_REPRODUCED"
MAGIC_CONTEXT_EXPERIMENT_SHA256 = (
    "c3e270a7278e433fea551899ae458196fb97cd3dfec6824d9633db46ef8cd054"
)
MAGIC_CONTEXT_DOCKERFILE_SHA256 = (
    "9b46dd58ed5b3b01c7df831a861ba89d7201d536668cf62af0f05b62afd0b64c"
)
MAGIC_CONTEXT_DOCTOR_SHA256 = (
    "ae0a5e9e643cfd3ade7d6b48c9403143d5589976d4d535e7fff62874feb85ebe"
)
GAAMA_REVISION = "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
GAAMA_STATUS = "GAAMA_COMPONENT_CONTRACT_PASS"
GAAMA_EXPERIMENT_SHA256 = (
    "b3e0422d40b4889c55457c48389962f5d4869940d5a74be5c5dbcc41260fd6c4"
)
GAAMA_DOCKERFILE_SHA256 = (
    "910e65eac12ca3ee82bfcc204ee5c9440bcedbd0f45da38452ba43a1363ffc98"
)
GAAMA_DOCTOR_SHA256 = (
    "9121773d078cd0f7a410aa1498aeb98d9a9900931dcbd64fbf140967f4a9957a"
)
GAAMA_NATURAL_STATUS = "GAAMA_NATURAL_GRAPH_PASS"
GAAMA_NATURAL_EXPERIMENT_SHA256 = (
    "68221e27874c67dcc4532e6a768fc84e5bcf36e284f0122f86455561633576b6"
)
GAAMA_NATURAL_DOCTOR_SHA256 = (
    "bc70ef62cd93d514024bc09472539ceb72a3e81b5f1e75e670ed5c98bacfc797"
)
GAAMA_NATURAL_MODULE_SHA256 = (
    "29c270f39c0459a313a469eafaa5b449751874f2f0cea2588d56ca771ac6ddc1"
)
HOLOGRAPHIC_REVISION = "a90d5369f76c87c98547d2e283aa26d5cfabf322"
HOLOGRAPHIC_STATUS = "BLOCKED_GLOBAL_SESSION_SCOPE_AND_NATIVE_SESSION_PURGE_REPRODUCED"
HOLOGRAPHIC_EXPERIMENT_SHA256 = (
    "bdd4bde610d1935457275885b642d218b79e2fbf72625d3feed6d467f7a2484a"
)
HOLOGRAPHIC_DOCKERFILE_SHA256 = (
    "a0b6cdca3430f8c88e868440451a95a86d0ce290baf963ef537ff44baa4644e0"
)
HOLOGRAPHIC_DOCTOR_SHA256 = (
    "4180324ad47029ecc759c278605fac15135db342d97348f2caf10d83eb1c5e43"
)
BYTEROVER_REVISION = "1f4609c18ca735810860b3ba9178cae2dd8a67b0"
BYTEROVER_TAG_OBJECT = "68ef7f91801e18ff50f361bd4cad5f36b8791789"
BYTEROVER_STATUS = "BLOCKED_OFFLINE_DAEMON_AND_PORTABLE_SESSION_LIFECYCLE_REPRODUCED"
BYTEROVER_EXPERIMENT_SHA256 = (
    "39c80cd1804da76d3a1a8a52a31a8083e99dfc2d6d1b93efab323d560019d0ab"
)
BYTEROVER_DOCKERFILE_SHA256 = (
    "8aa54f17f9b2c3faf4d2691f3863d929f2a9eac4a3f730e03a36302eb55b22dc"
)
BYTEROVER_DOCTOR_SHA256 = (
    "3924ffebb711730cba1bff1ec6f41b0e9ba27adfb1afc524466d9b00e4690fa0"
)
OPENVIKING_REVISION = "eeff5a497360aa4481cf32e18a0d9376f4412f4c"
OPENVIKING_STATUS = "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE"
OPENVIKING_EXPERIMENT_SHA256 = (
    "c0d038503ffa847059c8fd21be538f09f5ab43e265ccfbacab84b327373e8b95"
)
OPENVIKING_DOCTOR_SHA256 = (
    "1a1508e69bf1dd9b999938a2d4ccfdc48ef79d476f9773a1b701db5dd3bd252a"
)
HINDSIGHT_REVISION = "5781d28d8fcc717a15818330b12250b311957000"
HINDSIGHT_STATUS = "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE"
HINDSIGHT_EXPERIMENT_SHA256 = (
    "603d0ae2de5def6ab3f5ac56ef89159d4d18a6dc6ff11de5147c805ae143c6e6"
)
HINDSIGHT_DOCTOR_SHA256 = (
    "36392411d6d1bb9151631b35b66215e3784f37a9ae1135781d351b22b8ec726f"
)
MEM0_LIFECYCLE_REVISION = "71f2ebefa3494da21550fb525216818776cde67f"
MEM0_LIFECYCLE_SOURCE_ARCHIVE_SHA256 = (
    "c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12"
)
MEM0_LIFECYCLE_STATUS = "BLOCKED_ADAPTER_CRASH_RECOVERY"
MEM0_LIFECYCLE_EXPERIMENT_SHA256 = (
    "f9e77ea6997f1bc716240c0ec6416e54cb026a9ae78d5f8ecf479fcef25d5b42"
)
SUPERMEMORY_DOCUMENTATION_REVISION = "82dae50ef458139823b3bfd3ebaaaac90ffd8a7c"
SUPERMEMORY_RELEASE_REVISION = "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d"
SUPERMEMORY_STATUS = "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL"
SUPERMEMORY_EXPERIMENT_SHA256 = (
    "e6b6375de427aefb58f1595cb3d96631924fd89ab1699f8ef688e3fad99593aa"
)
SUPERMEMORY_DOCKERFILE_SHA256 = (
    "fb2986a62402cf08de792ad629aa1f8f42bc36663356c858ba795fcab26d7baf"
)
SUPERMEMORY_DOCTOR_SHA256 = (
    "2be53a93ba085ac3b285438a7d354caa035c752faa5d94d65a6d673e624ab560"
)
GRAPHITI_REVISION = "401c59a65bdeb22a44136901ff30231e6998a7fe"
GRAPHITI_STATUS = "BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH"
GRAPHITI_EXPERIMENT_SHA256 = (
    "6dfb4bf7f415378b8351870aeedda80881bb8842523bfc6ae4d7a1365d10526c"
)
GRAPHITI_SOURCE_ARCHIVE_SHA256 = (
    "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
)
GRAPHITI_RUNNER_SHA256 = (
    "6dece39c429cca3cb2d7dc87b1c6a845c479733930980aae50ffee90be03f450"
)
GRAPHITI_IMAGE_ID = (
    "sha256:de790ca9605b172009ca833ef82d3cf0761b8316be53a9d9ebbe5ca8ddc347b8"
)
ASTRA_REVISION = "644f9d4e65f4e725996025834c91531592ab6166"
ASTRA_TREE = "43592dc01aa730efb263d24255b094e1f4dc24f3"
ASTRA_ARCHIVE_SHA256 = (
    "f283ca328a080bd6c8c7fac723d490f3d73d15a71f0b7290090bd371957f3d48"
)
ASTRA_LICENSE_SHA256 = (
    "f109128ffcc7d51c9f9ee414f04b7b2c6a633808b4d565138ca43e0c77dbd86a"
)
ASTRA_LOCK_SHA256 = (
    "44ffc76a024117bd76488a4878e8b372c9aab9abe1abfd9489bf17135218c2b5"
)
ASTRA_PACKAGE_SHA256 = (
    "a45d6da6de09c5c96443f4c7ff129aed9bc99ce2c3ccc76fb56bed33cfc53a9d"
)
ASTRA_IMAGE_ID = (
    "sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c"
)
ASTRA_IMAGE_DIGEST = (
    "node@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c"
)
ASTRA_STATUS = "ASTRA_WORKING_SET_COMPONENT_CONFORMANCE_PASS"
PROVIDER_ROSTER = [
    "byterover",
    "hindsight",
    "holographic",
    "honcho",
    "mem0",
    "memori",
    "openviking",
    "retaindb",
    "supermemory",
]
TOTAL_REQUIRED_FILES = {
    "experiment.yaml",
    "input-receipt.json",
    "manifest.json",
    "native-report.json",
    "report.json",
    "runtime-receipt.json",
    "source-receipt.json",
}
HERMES_RESULT_STATUS = {
    "byterover": "PASS",
    "common": "PASS",
    "hindsight": "PASS",
    "hindsight-strict-timeout-probe": "FAIL",
    "holographic": "PASS",
    "honcho": "FAIL",
    "mem0": "PASS",
    "memori": "PASS",
    "memori-install-discovery": "PASS",
    "openviking": "PASS",
    "retaindb": "PASS",
    "supermemory": "PASS",
}
HERMES_LOG_ROSTER = {f"{group}.log" for group in HERMES_RESULT_STATUS}
NEO4J_REQUIRED_FILES = {"experiment.yaml", "manifest.json", "report.json"}
HIPPO_RUN_FILES = {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in (
        "prepare.argv.json",
        "prepare.json",
        "prepare.stderr",
        "purge.argv.json",
        "purge.json",
        "purge.stderr",
        "restart.argv.json",
        "restart.json",
        "restart.stderr",
        "stable-projection.json",
    )
}
HIPPO_REQUIRED_FILES = {
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "source-receipt.json",
} | HIPPO_RUN_FILES
MAGIC_CONTEXT_RUN_FILES = {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in (
        "alias.argv.json",
        "alias.json",
        "alias.stderr",
        "prepare.argv.json",
        "prepare.json",
        "prepare.stderr",
        "purge.argv.json",
        "purge.json",
        "purge.stderr",
        "restart.argv.json",
        "restart.json",
        "restart.stderr",
        "stable-projection.json",
    )
}
MAGIC_CONTEXT_REQUIRED_FILES = {
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "source-receipt.json",
} | MAGIC_CONTEXT_RUN_FILES
GAAMA_REQUIRED_FILES = {
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "run-1/argv.json",
    "run-1/report.json",
    "run-2/argv.json",
    "run-2/report.json",
    "source-receipt.json",
}
GAAMA_NATURAL_REQUIRED_FILES = set(GAAMA_REQUIRED_FILES) | {"source/locomo10.json"}
HOLOGRAPHIC_RUN_FILES = {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in (
        "prepare.argv.json",
        "prepare.json",
        "prepare.stderr",
        "purge.argv.json",
        "purge.json",
        "purge.stderr",
        "restart.argv.json",
        "restart.json",
        "restart.stderr",
        "stable-projection.json",
    )
}
HOLOGRAPHIC_REQUIRED_FILES = {
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "source-receipt.json",
} | HOLOGRAPHIC_RUN_FILES
BYTEROVER_RUN_FILES = {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in (
        "prepare.argv.json",
        "prepare.json",
        "prepare.stderr",
        "restart.argv.json",
        "restart.json",
        "restart.stderr",
        "stable-projection.json",
    )
}
BYTEROVER_REQUIRED_FILES = {
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "source-receipt.json",
} | BYTEROVER_RUN_FILES
OPENVIKING_REQUIRED_FILES = {"experiment.yaml"} | {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in ("manifest.json", "report.json")
}
MEM0_LIFECYCLE_CODE_FILES = {
    "harness/memory_trials/lifecycle.py",
    "infra/memory-baselines/mem0_lifecycle_sidecar.py",
    "infra/memory-baselines/mem0_sidecar.py",
    "scripts/run_mem0_lifecycle_doctor.py",
    "scripts/validate_mem0_lifecycle_experiment.py",
}
MEM0_LIFECYCLE_REQUIRED_FILES = {
    "dockerfile",
    "experiment.yaml",
    "image-inspect.json",
    "source-context.json",
    *MEM0_LIFECYCLE_CODE_FILES,
    *{
        f"run-{run}/{name}"
        for run in (1, 2)
        for name in ("manifest.json", "report.json", "stderr.txt", "stdout.txt")
    },
}
SUPERMEMORY_RUN_FILES = {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in (
        "forget.argv.json",
        "forget.json",
        "forget.stderr",
        "prepare.argv.json",
        "prepare.json",
        "prepare.stderr",
        "restart.argv.json",
        "restart.json",
        "restart.stderr",
        "stable-projection.json",
    )
}
SUPERMEMORY_REQUIRED_FILES = {
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "source-receipt.json",
} | SUPERMEMORY_RUN_FILES
GRAPHITI_REQUIRED_FILES = {
    "image-inspect.json",
    "manifest.json",
    "module-architecture.json",
    "registered-experiment.yaml",
    "report.json",
    "run-1.json",
    "run-2.json",
}
OPENVIKING_OPERATION_SEQUENCE = [
    "tenant-a-write",
    "tenant-a-restart-search",
    "tenant-b-cannot-see-a",
    "tenant-b-write",
    "tenant-a-cannot-see-b",
    "tenant-a-restart-read",
    "tenant-a-forget",
    "tenant-b-forget",
    "tenant-a-delete-survives-restart",
    "tenant-b-delete-survives-restart",
]
HINDSIGHT_REQUIRED_FILES = {"experiment.yaml"} | {
    f"run-{run}/{name}"
    for run in (1, 2)
    for name in ("manifest.json", "report.json")
}
HINDSIGHT_OPERATION_SEQUENCE = [
    "tenant-a-tool-retain",
    "tenant-a-prefetch",
    "tenant-b-cannot-see-a",
    "tenant-b-sync-turn-retain",
    "tenant-b-search-own",
    "tenant-a-cannot-see-b",
    "tenant-a-full-restart-search",
    "tenant-b-full-restart-search",
    "tenant-a-admin-delete",
    "tenant-b-admin-delete",
    "tenant-a-delete-survives-full-restart",
    "tenant-b-delete-survives-full-restart",
]
ASTRA_REQUIRED_FILES = {
    "node-image-inspect.json",
    "vitest-run1.json",
    "vitest-run2.json",
}
ASTRA_SUITE_COUNTS = {
    "tests/guards.test.ts": 7,
    "tests/memory-window.test.ts": 7,
    "tests/retrieval.test.ts": 12,
}


class EvidenceError(ValueError):
    """Raised when local result bytes do not satisfy the evidence contract."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _decode_json(data: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvidenceError(f"{owner} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{owner} must be a JSON mapping")
    return value


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"evidence input is not a regular file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceError(f"evidence JSON must be a mapping: {path}")
    return value


def _capture_files(root: Path) -> dict[str, dict[str, Any]]:
    if root.is_symlink() or not root.is_dir():
        raise EvidenceError(f"evidence root is not a regular directory: {root}")
    captured: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvidenceError(f"evidence tree contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        captured[relative] = {
            "bytes": len(data),
            "sha256": _sha256(data),
            "content_base64": base64.b64encode(data).decode("ascii"),
        }
    if not captured:
        raise EvidenceError(f"evidence root contains no files: {root}")
    return captured


def _capture_files_compressed(root: Path) -> dict[str, dict[str, Any]]:
    """Capture an evidence tree with deterministic gzip for large artifacts."""

    captured = _capture_files(root)
    for receipt in captured.values():
        data = base64.b64decode(receipt.pop("content_base64"))
        if len(data) >= 1_000_000:
            receipt["encoding"] = "gzip"
            receipt["content_gzip_base64"] = base64.b64encode(
                gzip.compress(data, compresslevel=9, mtime=0)
            ).decode("ascii")
        else:
            receipt["content_base64"] = base64.b64encode(data).decode("ascii")
    return captured


def _decode_captured_files(files: dict[str, dict[str, Any]]) -> dict[str, bytes]:
    decoded: dict[str, bytes] = {}
    for name, receipt in files.items():
        if receipt.get("encoding") == "gzip":
            try:
                data = gzip.decompress(base64.b64decode(receipt["content_gzip_base64"]))
            except (KeyError, ValueError, gzip.BadGzipFile) as exc:
                raise EvidenceError(f"compressed evidence is invalid: {name}") from exc
        else:
            try:
                data = base64.b64decode(receipt["content_base64"])
            except (KeyError, ValueError) as exc:
                raise EvidenceError(f"evidence encoding is invalid: {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha256(data):
            raise EvidenceError(f"evidence receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _allmem_semantic_projection(projection: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(projection))
    normalized.pop("sha256", None)
    source_content = {
        row["source_id"]: row["content_sha256"]
        for row in normalized.get("nodes", [])
        if isinstance(row, dict) and row.get("source_id") is not None
    }
    query = normalized.get("query")
    if not isinstance(query, dict):
        raise EvidenceError("All-Mem projection query is missing")
    ranked = query.pop("ranked_source_ids", None)
    if not isinstance(ranked, list) or not all(isinstance(item, str) for item in ranked):
        raise EvidenceError("All-Mem ranked source IDs are invalid")
    query["ranked_content_sha256"] = [
        source_content.get(source_id, f"missing:{source_id}") for source_id in ranked
    ]
    return normalized


def _allmem_projection_sha256(projection: dict[str, Any]) -> str:
    return _sha256(
        json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    )


def validate_allmem_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the complete All-Mem topology-negative evidence contract."""

    root_files = {
        "Dockerfile",
        "doctor.py",
        "experiment.yaml",
        "image-inspect.json",
        "manifest.json",
        "report.json",
        "run_allmem_topology_doctor.py",
        "source-receipt.json",
        "validate_allmem_topology_experiment.py",
    }
    run_files = {
        f"run-{run}/{name}"
        for run in (1, 2)
        for name in (
            "graph.pkl",
            "prepare.argv.json",
            "prepare.json",
            "prepare.stderr",
            "verify.argv.json",
            "verify.json",
            "verify.stderr",
        )
    }
    if set(files) != root_files | run_files:
        raise EvidenceError("All-Mem evidence file roster drifted")
    expected_hashes = {
        "experiment.yaml": ALLMEM_EXPERIMENT_SHA256,
        "Dockerfile": ALLMEM_DOCKERFILE_SHA256,
        "doctor.py": ALLMEM_DOCTOR_SHA256,
        "run_allmem_topology_doctor.py": ALLMEM_RUNNER_SHA256,
        "validate_allmem_topology_experiment.py": ALLMEM_VALIDATOR_SHA256,
    }
    for name, expected in expected_hashes.items():
        if _sha256(files[name]) != expected:
            raise EvidenceError(f"All-Mem registered input drifted: {name}")

    manifest = _decode_json(files["manifest.json"], "All-Mem manifest")
    report = _decode_json(files["report.json"], "All-Mem report")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != "SEALED_ALLMEM_TOPOLOGY_NEGATIVE"
        or manifest.get("source_id") != "all-mem"
        or manifest.get("report_sha256") != _sha256(files["report.json"])
    ):
        raise EvidenceError("All-Mem manifest identity drifted")
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, dict) or set(manifest_files) != set(files) - {
        "manifest.json"
    }:
        raise EvidenceError("All-Mem manifest file roster drifted")
    for name, receipt in manifest_files.items():
        if (
            not isinstance(receipt, dict)
            or receipt.get("bytes") != len(files[name])
            or receipt.get("sha256") != _sha256(files[name])
        ):
            raise EvidenceError(f"All-Mem manifest receipt drifted: {name}")

    source = _decode_json(files["source-receipt.json"], "All-Mem source receipt")
    image_rows = json.loads(files["image-inspect.json"])
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("All-Mem image inspection drifted")
    image = image_rows[0]
    if (
        report.get("schema_version") != 1
        or report.get("source_id") != "all-mem"
        or report.get("status") != ALLMEM_STATUS
        or report.get("evidence_kind") != "native-negative-reproduction"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("runtime_lane") != "local-arm64-docker-network-none"
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("source_revisions")
        != {"https://github.com/LvCan926/All-Mem": ALLMEM_REVISION}
        or report.get("container", {}).get("image_id") != image.get("Id")
        or report.get("container", {}).get("inspect_sha256")
        != _sha256(files["image-inspect.json"])
    ):
        raise EvidenceError("All-Mem report identity or provenance drifted")
    expected_labels = report["container"].get("labels")
    if image.get("Config", {}).get("Labels") != expected_labels:
        raise EvidenceError("All-Mem live image labels drifted")
    if source.get("revision") != ALLMEM_REVISION or source.get("worktree_clean") is not True:
        raise EvidenceError("All-Mem source identity drifted")

    semantic_roots: list[str] = []
    execution_roots: list[str] = []
    exact_equal: list[bool] = []
    observed_orders: set[tuple[str, ...]] = set()
    report_runs = report.get("runs")
    if not isinstance(report_runs, list) or len(report_runs) != 2:
        raise EvidenceError("All-Mem report run roster drifted")
    for run in (1, 2):
        row = report_runs[run - 1]
        if not isinstance(row, dict) or row.get("run") != run:
            raise EvidenceError("All-Mem report run identity drifted")
        phases: dict[str, dict[str, Any]] = {}
        argvs: dict[str, list[str]] = {}
        for phase in ("prepare", "verify"):
            payload = _decode_json(
                files[f"run-{run}/{phase}.json"], f"All-Mem run {run} {phase}"
            )
            argv = json.loads(files[f"run-{run}/{phase}.argv.json"])
            if (
                not isinstance(argv, list)
                or "--network" not in argv
                or argv[argv.index("--network") + 1] != "none"
                or "--read-only" not in argv
                or argv.count("--cap-drop") != 1
                or argv[argv.index("--cap-drop") + 1] != "ALL"
                or argv.count("--security-opt") != 1
                or argv[argv.index("--security-opt") + 1]
                != "no-new-privileges"
                or payload.get("phase") != phase
                or payload.get("status") != ALLMEM_STATUS
                or payload.get("external_model_calls") != 0
            ):
                raise EvidenceError(f"All-Mem run {run} {phase} contract drifted")
            projection = payload.get("projection")
            if not isinstance(projection, dict):
                raise EvidenceError("All-Mem projection is missing")
            claimed_projection_sha = projection.get("sha256")
            projection_without_sha = dict(projection)
            projection_without_sha.pop("sha256", None)
            if claimed_projection_sha != _allmem_projection_sha256(
                projection_without_sha
            ):
                raise EvidenceError("All-Mem native projection hash drifted")
            if (
                projection.get("recovery")
                != {"update": True, "split": False, "merge_a": False, "merge_b": False}
                or projection.get("derived_source_labels_without_raw_path") is not True
                or projection.get("query", {}).get("update_old_recovered") is not True
            ):
                raise EvidenceError("All-Mem recovery falsifier drifted")
            phases[phase] = payload
            argvs[phase] = argv
            observed_orders.add(tuple(projection["query"]["ranked_source_ids"]))
        prepare_projection = phases["prepare"]["projection"]
        verify_projection = phases["verify"]["projection"]
        prepare_semantic = _allmem_projection_sha256(
            _allmem_semantic_projection(prepare_projection)
        )
        verify_semantic = _allmem_projection_sha256(
            _allmem_semantic_projection(verify_projection)
        )
        if prepare_semantic != verify_semantic:
            raise EvidenceError("All-Mem fresh-restart semantic projection drifted")
        semantic_roots.append(prepare_semantic)
        equal = prepare_projection == verify_projection
        exact_equal.append(equal)
        graph_sha = _sha256(files[f"run-{run}/graph.pkl"])
        if len(files[f"run-{run}/graph.pkl"]) < 16 or row.get("state_file_sha256") != graph_sha:
            raise EvidenceError("All-Mem persisted graph receipt drifted")
        if (
            row.get("semantic_projection_sha256") != prepare_semantic
            or row.get("exact_projection_equal") is not equal
            or row.get("prepare_projection_sha256") != prepare_projection["sha256"]
            or row.get("verify_projection_sha256") != verify_projection["sha256"]
        ):
            raise EvidenceError("All-Mem run summary drifted")
        execution_roots.append(
            _sha256(
                _canonical_json(
                    {
                        "argvs": argvs,
                        "graph_sha256": graph_sha,
                        "prepare_sha256": _sha256(files[f"run-{run}/prepare.json"]),
                        "verify_sha256": _sha256(files[f"run-{run}/verify.json"]),
                    }
                )
            )
        )
    if len(set(semantic_roots)) != 1:
        raise EvidenceError("All-Mem clean-state semantic projections drifted")
    if (
        report.get("stable_semantic_projection_sha256") != semantic_roots[0]
        or report.get("fresh_restart_exact_projection_equal_all") is not all(exact_equal)
        or report.get("observed_rank_orders")
        != [list(order) for order in sorted(observed_orders)]
        or report.get("claim_boundary", {}).get("split_merge_raw_recovery_failed")
        is not True
        or report.get("claim_boundary", {}).get("h100_admission")
        != "forbidden-for-this-revision"
    ):
        raise EvidenceError("All-Mem aggregate claim boundary drifted")
    return {
        "manifest_root": _sha256(files["manifest.json"]),
        "image_id": image["Id"],
        "stable_semantic_projection_sha256": semantic_roots[0],
        "execution_identity_sha256s": execution_roots,
        "observed_rank_orders": [list(order) for order in sorted(observed_orders)],
    }


def _verify_manifest(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = _json(root / "manifest.json")
    captured = _capture_files(root)
    validate_total_recall_files(
        {name: base64.b64decode(receipt["content_base64"]) for name, receipt in captured.items()}
    )
    return manifest, captured


def validate_total_recall_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the complete semantic contract for one Total Recall run."""

    if set(files) != TOTAL_REQUIRED_FILES:
        raise EvidenceError("Total Recall file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Total Recall manifest")
    if manifest.get("schema_version") != 1 or manifest.get("status") != TOTAL_STATUS:
        raise EvidenceError("Total Recall manifest identity drifted")
    manifest_without_root = dict(manifest)
    manifest_root = manifest_without_root.pop("manifest_sha256", None)
    if manifest_root != _sha256(_canonical_json(manifest_without_root)):
        raise EvidenceError("Total Recall manifest self-root drifted")
    artifacts = manifest.get("artifacts")
    expected_artifacts = TOTAL_REQUIRED_FILES - {"manifest.json"}
    if not isinstance(artifacts, dict) or set(artifacts) != expected_artifacts:
        raise EvidenceError("Total Recall manifest artifact roster drifted")
    for name in sorted(expected_artifacts):
        receipt = artifacts[name]
        if not isinstance(receipt, dict):
            raise EvidenceError(f"Total Recall artifact receipt is invalid: {name}")
        if receipt != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"Total Recall artifact receipt drifted: {name}")

    report = _decode_json(files["report.json"], "Total Recall report")
    native = _decode_json(files["native-report.json"], "Total Recall native report")
    source = _decode_json(files["source-receipt.json"], "Total Recall source receipt")
    runtime = _decode_json(files["runtime-receipt.json"], "Total Recall runtime receipt")
    input_receipt = _decode_json(files["input-receipt.json"], "Total Recall input receipt")
    if (
        report.get("status") != TOTAL_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_admission") != "blocked"
        or report.get("native_report") != native
        or report.get("source_receipt") != source
        or report.get("runtime_receipt") != runtime
        or report.get("input_receipt") != input_receipt
    ):
        raise EvidenceError("Total Recall report does not bind its child receipts")
    expected_gates = {
        "automatic_compactor_moved_exactly_one_row": True,
        "automatic_row_deleted_by_restart_cleanup": True,
        "automatic_row_present_before_restart": True,
        "automatic_row_vector_missing_before_restart": True,
        "manual_vector_preserving_control_present_before_restart": True,
        "manual_vector_preserving_control_survives_restart": True,
    }
    expected_automatic = {
        "id": "doctor-auto-demotion",
        "post_restart_content_rows": 0,
        "post_restart_vector_rows": 0,
        "pre_restart_content_rows": 1,
        "pre_restart_vector_rows": 0,
    }
    expected_control = {
        "id": "doctor-vector-preserving-control",
        "post_restart_content_rows": 1,
        "post_restart_vector_rows": 1,
        "pre_restart_content_rows": 1,
        "pre_restart_vector_rows": 1,
    }
    if (
        native.get("schema_version") != 1
        or native.get("doctor") != "total-recall-native-auto-demotion-restart-v1"
        or native.get("status") != TOTAL_STATUS
        or native.get("source_revision") != TOTAL_REVISION
        or native.get("expected_negative_finding") is not True
        or native.get("scientific_result") is not False
        or native.get("publication_ready") is not False
        or native.get("gates") != expected_gates
        or native.get("automatic_transition") != expected_automatic
        or native.get("vector_preserving_control") != expected_control
    ):
        raise EvidenceError("Total Recall native negative semantics drifted")
    if source.get("git_sha") != TOTAL_REVISION:
        raise EvidenceError("Total Recall source revision drifted")
    image_id = runtime.get("image_id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise EvidenceError("Total Recall image identity is invalid")
    return {
        "manifest_root": manifest_root,
        "execution_identity_sha256": _sha256(files["native-report.json"]),
        "projection": _total_projection(report),
        "input_receipt": input_receipt,
        "image_id": image_id,
    }


def validate_hippo_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the complete two-run Hippo negative-evidence contract."""

    if set(files) != HIPPO_REQUIRED_FILES:
        raise EvidenceError("Hippo evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Hippo manifest")
    expected_artifacts = HIPPO_REQUIRED_FILES - {"manifest.json"}
    artifacts = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != HIPPO_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("Hippo manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        if artifacts[name] != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"Hippo artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("Hippo manifest root drifted")

    report = _decode_json(files["report.json"], "Hippo report")
    source = _decode_json(files["source-receipt.json"], "Hippo source receipt")
    inspect = _decode_json(files["image-inspect.json"], "Hippo image inspect")
    expected_findings = {
        "active_inactive_paging_supported": False,
        "cross_tenant_semantic_created": True,
        "cross_tenant_semantic_owned_by_default_tenant": True,
        "cross_tenant_semantic_retrievable_by_default_tenant": True,
        "cross_tenant_semantic_source_lineage_complete": False,
        "logical_delete_reaches_zero_rows": True,
        "plaintext_canary_residue_in_sqlite": True,
        "positive_outcome_extends_retention": True,
        "working_memory_eviction_is_deletion": True,
        "working_memory_flush_archives": False,
    }
    expected_admission = {
        "active_inactive_h100": "forbidden-for-this-revision",
        "cluster_confirmation": "not-run",
        "retention_actor_pilot": "blocked",
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "hippo-retention-cross-tenant-doctor-v1"
        or report.get("status") != HIPPO_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("findings") != expected_findings
        or report.get("admission") != expected_admission
    ):
        raise EvidenceError("Hippo negative result semantics drifted")
    if (
        source.get("repository") != "https://github.com/kitfunso/hippo-memory"
        or source.get("revision") != HIPPO_REVISION
        or source.get("tree") != "88d0613e1e5aaec6d1c401c200d5ad3372af0828"
        or source.get("git_archive_tar_sha256")
        != "d966a02bf1c811f191e94fa21317a3a2a3a9797ff7f3da93caa114a794845bb8"
        or source.get("dockerfile_sha256") != HIPPO_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != HIPPO_DOCTOR_SHA256
        or source.get("worktree_clean") is not True
    ):
        raise EvidenceError("Hippo source receipt drifted")
    if _sha256(files["experiment.yaml"]) != HIPPO_EXPERIMENT_SHA256:
        raise EvidenceError("Hippo registered experiment drifted")
    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != HIPPO_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != source["git_archive_tar_sha256"]
    ):
        raise EvidenceError("Hippo image receipt drifted")

    projections: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    for run in (1, 2):
        prefix = f"run-{run}"
        prepare = _decode_json(files[f"{prefix}/prepare.json"], "Hippo prepare")
        restart = _decode_json(files[f"{prefix}/restart.json"], "Hippo restart")
        purge = _decode_json(files[f"{prefix}/purge.json"], "Hippo purge")
        projection = _decode_json(
            files[f"{prefix}/stable-projection.json"], "Hippo stable projection"
        )
        if (
            prepare.get("phase") != "prepare"
            or restart.get("phase") != "restart"
            or purge.get("phase") != "purge"
            or prepare.get("projection_sha256") != restart.get("projection_sha256")
            or prepare.get("cross_tenant", {}).get("mixed_semantic_created") is not True
            or prepare.get("cross_tenant", {}).get("mixed_semantic_tenant_id") != "default"
            or prepare.get("cross_tenant", {}).get("default_tenant_retrievable") is not True
            or prepare.get("cross_tenant", {}).get("source_lineage_complete") is not False
            or prepare.get("retention", {}).get("positive_outcome_extends_retention") is not True
            or purge.get("logical_record_count") != 0
            or purge.get("native_scoped_purge_available") is not False
            or purge.get("plaintext_residue_reproduced") is not True
            or not purge.get("physical_hits")
            or projection.get("cross_tenant") != prepare.get("cross_tenant")
            or projection.get("retention") != prepare.get("retention")
            or projection.get("purge", {}).get("physical_hits") != purge.get("physical_hits")
        ):
            raise EvidenceError("Hippo run semantics drifted")
        if _sha256(_canonical_json(projection)) != report.get("stable_projection_sha256"):
            raise EvidenceError("Hippo stable projection root drifted")
        phase_argv = []
        for phase in ("prepare", "restart", "purge"):
            argv = json.loads(files[f"{prefix}/{phase}.argv.json"])
            if (
                not isinstance(argv, list)
                or "--network" not in argv
                or argv[argv.index("--network") + 1] != "none"
                or "--read-only" not in argv
                or "--cap-drop" not in argv
                or argv[argv.index("--cap-drop") + 1] != "ALL"
                or "no-new-privileges" not in argv
                or argv[-2:] != [image_id, phase]
            ):
                raise EvidenceError("Hippo contained execution argv drifted")
            phase_argv.append(argv)
        projections.append(projection)
        execution_identities.append(_sha256(_canonical_json(phase_argv)))
    if projections[0] != projections[1] or len(set(execution_identities)) != 2:
        raise EvidenceError("Hippo clean-state repetitions are not distinct and equal")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "stable_projection": projections[0],
        "execution_identities": execution_identities,
    }


def validate_supermemory_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the two-run Supermemory binary-only negative contract."""

    if set(files) != SUPERMEMORY_REQUIRED_FILES:
        raise EvidenceError("Supermemory evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Supermemory manifest")
    expected_artifacts = SUPERMEMORY_REQUIRED_FILES - {"manifest.json"}
    artifacts = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != SUPERMEMORY_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("Supermemory manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        expected = {"bytes": len(files[name]), "sha256": _sha256(files[name])}
        if artifacts[name] != expected:
            raise EvidenceError(f"Supermemory artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("Supermemory manifest root drifted")

    report = _decode_json(files["report.json"], "Supermemory report")
    source = _decode_json(files["source-receipt.json"], "Supermemory source receipt")
    inspect = _decode_json(files["image-inspect.json"], "Supermemory image inspect")
    expected_findings = {
        "acknowledged_writes_survive_sigkill_restart": False,
        "cross_container_plaintext_disclosure": False,
        "direct_memory_crud_works": True,
        "graceful_restart_persists_acknowledged_pair": True,
        "native_tenant_scoped_physical_purge_available": False,
        "provider_plaintext_at_rest_detected": False,
        "release_v003_ignores_current_remote_embedding_configuration": True,
        "soft_forget_excludes_normal_reads": True,
        "versioned_update_and_history_work": True,
    }
    expected_admission = {
        "cluster_confirmation": "not-run",
        "memory_lifecycle_h100": "forbidden-for-this-release",
        "reason": (
            "acknowledged writes lost on SIGKILL, binary-only server, and no "
            "tenant-scoped physical purge"
        ),
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "supermemory-local-binary-doctor-v1"
        or report.get("status") != SUPERMEMORY_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("source_evidence") != "binary-only-release-artifact"
        or report.get("local_server_source_available") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("findings") != expected_findings
        or report.get("admission") != expected_admission
    ):
        raise EvidenceError("Supermemory negative result semantics drifted")
    binary = source.get("binary_artifact", {})
    model = source.get("embedding_model", {})
    if (
        source.get("repository") != "https://github.com/supermemoryai/supermemory"
        or source.get("documentation_revision") != SUPERMEMORY_DOCUMENTATION_REVISION
        or source.get("documentation_tree")
        != "5c58a2b231ea606683bf7b258d16f0155de31f8c"
        or source.get("documentation_archive_tar_sha256")
        != "367af62b9353b89aea57942def25e20acad7a4eae8a2434b3e209a9a1d932667"
        or source.get("release_revision") != SUPERMEMORY_RELEASE_REVISION
        or source.get("release_tree")
        != "ca1cf46027d94fe3307bbf063a2ddb635d6b7b88"
        or source.get("release_archive_tar_sha256")
        != "f515205dede24fc7f2402ef9d6b34c8002d8fee5d81331ace363f4d73803faf9"
        or source.get("release_tree_path_list_sha256")
        != "85226b9fd290c6965c9e1c71653638afc0b062abb1b546c50834b5b26ca22483"
        or source.get("release_tree_file_count") != 953
        or source.get("local_server_source_candidates") != []
        or source.get("local_server_source_available") is not False
        or source.get("dockerfile_sha256") != SUPERMEMORY_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != SUPERMEMORY_DOCTOR_SHA256
        or source.get("worktree_clean") is not True
        or binary.get("sha256")
        != "167f595afdb6fba3f6ef12e23b31aa99d177684b188376072d4b46f60d3b4d8e"
        or binary.get("bytes") != 214_510_741
        or binary.get("manifest_sha256")
        != "2b05221afcc6936a25a97cf2602aedf1a51775f8181348f18c66711a6cc6e0e9"
        or binary.get("manifest", {}).get("platforms", {})
        .get("linux-arm64", {})
        .get("checksum")
        != binary.get("sha256")
        or model.get("revision") != "4d6cd88e18e51a5e020c2c305726d76ada9c03cf"
    ):
        raise EvidenceError("Supermemory source receipt drifted")
    expected_model_files = {
        "Xenova/bge-base-en-v1.5/config.json": (
            "d83c21fa7366994560727112ef0a31d8a2ec1c280c2a3e66326fdb877f64c91e"
        ),
        "Xenova/bge-base-en-v1.5/onnx/model_quantized.onnx": (
            "c9729cc84cbd0e9fecc759505d2be65916c9fe05222d7ea26c65fcb3382af38d"
        ),
        "Xenova/bge-base-en-v1.5/tokenizer.json": (
            "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"
        ),
        "Xenova/bge-base-en-v1.5/tokenizer_config.json": (
            "9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3"
        ),
    }
    if model.get("files") != expected_model_files:
        raise EvidenceError("Supermemory embedding receipt drifted")
    if _sha256(files["experiment.yaml"]) != SUPERMEMORY_EXPERIMENT_SHA256:
        raise EvidenceError("Supermemory registered experiment drifted")

    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or report.get("image", {}).get("inspect_sha256")
        != "e4fd24d90c400c1a5adfe2855f442e115ff28459b28977c4823c476c82231d26"
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or inspect.get("Config", {}).get("Entrypoint")
        != ["python", "/opt/cotcodec/doctor.py"]
        or inspect.get("Config", {}).get("Cmd") is not None
        or labels.get("org.opencontainers.image.revision")
        != SUPERMEMORY_DOCUMENTATION_REVISION
        or labels.get("org.cotcodec.supermemory-release-revision")
        != SUPERMEMORY_RELEASE_REVISION
        or labels.get("org.cotcodec.supermemory-binary-sha256")
        != binary.get("sha256")
        or labels.get("org.cotcodec.supermemory-model-revision")
        != model.get("revision")
        or labels.get("org.cotcodec.evidence-role")
        != "binary-only-cpu-lifecycle-doctor"
    ):
        raise EvidenceError("Supermemory image receipt drifted")

    projections: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    run_volumes: list[str] = []
    expected_argv_prefix = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        "2560m",
        "--cpus",
        "2",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532",
        "-v",
    ]
    expected_execution_receipts = {
        1: {
            "prepare_response_sha256": {
                "create_a": (
                    "dcb06a2509f58100db5896cddcf498ba3fad79d4ac34a6b432295d6bc90ff7f5"
                ),
                "create_b": (
                    "35efe2819d26288c47be3350d02732b293ce02fb38917ce973d2729e8e7f1e05"
                ),
                "list_a": (
                    "8cce46eeb09faed8686c60e6101370fef6e40ee7bbe0d998f895f429a3441ce7"
                ),
                "list_b": (
                    "8348125294c1e9794f7984dec537cc91be999cbabcff91e4ca2f35b351e336f7"
                ),
                "update_a": (
                    "4222c9f1ff0c69a883148e6b4d95fa2f80b06993d9ca9c5b261ea61db8eed9ae"
                ),
            },
            "forget_response_sha256": (
                "acbb224d664ced9a634332877af9cef68229b93bb25de397be1889952cc8272d"
            ),
            "state_manifest_sha256": (
                "73da36f0e56275ef6c6b3783bfaf7f5125e0140c814a6e5baf979f0a932e46a6"
            ),
        },
        2: {
            "prepare_response_sha256": {
                "create_a": (
                    "7cf49bc7e24fbd087362f1004799f2fe840b6ca50b6b1eb1cb5bc18096ed0d7b"
                ),
                "create_b": (
                    "b7731ac8721d8fee81ff10d796e8e99cb4d5f510ec51625ebe17e9cc4ba38f62"
                ),
                "list_a": (
                    "19e8b968ab8bab201cfb940ae49f7a7b6bce0bfe9d83888e9ded296f0b47ac1e"
                ),
                "list_b": (
                    "e52ac7b2c0841ea275a41423f8072bd463828737cbd864d458a756db4ff4b15e"
                ),
                "update_a": (
                    "c4c93034399cbe2438c627d1fd15b06f360175a14dddae2a59ec4fbd695f1f7e"
                ),
            },
            "forget_response_sha256": (
                "5c480fd95bafdb516fa18fda47c514c0ed26205a1643c0aaa7c87fdb4437b6fc"
            ),
            "state_manifest_sha256": (
                "6ddc66012fd5a2ee8c9e9dbba6959c7e40cbcb1eb940769a7e2ec1afff22300c"
            ),
        },
    }
    for run in (1, 2):
        prefix = f"run-{run}"
        prepare = _decode_json(files[f"{prefix}/prepare.json"], "Supermemory prepare")
        restart = _decode_json(files[f"{prefix}/restart.json"], "Supermemory restart")
        forget = _decode_json(files[f"{prefix}/forget.json"], "Supermemory forget")
        projection = _decode_json(
            files[f"{prefix}/stable-projection.json"],
            "Supermemory stable projection",
        )
        expected_prepare = {
            "direct_create": True,
            "superseded_not_searchable": True,
            "tenant_a_retrieval": True,
            "tenant_b_retrieval": True,
            "version_history_preserved": True,
            "versioned_update": True,
        }
        expected_restart = {
            "acknowledged_tenant_a_survives_sigkill": False,
            "acknowledged_tenant_b_survives_sigkill": False,
            "cross_tenant_plaintext_disclosure": False,
            "recovery_pair_committed_before_graceful_stop": True,
            "version_history_survives_sigkill": False,
        }
        expected_counts = {
            "tenant_a_latest_after_sigkill": 0,
            "tenant_b_latest_after_sigkill": 0,
        }
        expected_forget = {
            "graceful_restart_persists_acknowledged_pair": True,
            "native_tenant_scoped_physical_purge_available": False,
            "other_tenant_survives": True,
            "provider_plaintext_at_rest_detected": False,
            "soft_forget_excludes_normal_list": True,
            "soft_forget_excludes_normal_search": True,
        }
        execution_receipt = expected_execution_receipts[run]
        if (
            prepare.get("phase") != "prepare"
            or prepare.get("crash_injected_after_committed_update") is not True
            or prepare.get("checks") != expected_prepare
            or restart.get("phase") != "restart"
            or restart.get("checks") != expected_restart
            or restart.get("counts") != expected_counts
            or forget.get("phase") != "forget"
            or forget.get("checks") != expected_forget
            or forget.get("plaintext_hits") != []
            or forget.get("state_file_count") != 43
            or prepare.get("response_sha256")
            != execution_receipt["prepare_response_sha256"]
            or forget.get("response_sha256")
            != execution_receipt["forget_response_sha256"]
            or forget.get("state_manifest_sha256")
            != execution_receipt["state_manifest_sha256"]
            or projection.get("prepare") != expected_prepare
            or projection.get("restart")
            != {"checks": expected_restart, "counts": expected_counts}
            or projection.get("forget")
            != {"checks": expected_forget, "plaintext_hits": []}
        ):
            raise EvidenceError("Supermemory run semantics drifted")
        if _sha256(_canonical_json(projection)) != report.get(
            "stable_projection_sha256"
        ):
            raise EvidenceError("Supermemory stable projection root drifted")
        phase_argv = []
        volume_arg: str | None = None
        for phase in ("prepare", "restart", "forget"):
            argv = json.loads(files[f"{prefix}/{phase}.argv.json"])
            if (
                not isinstance(argv, list)
                or len(argv) != len(expected_argv_prefix) + 3
                or argv[: len(expected_argv_prefix)] != expected_argv_prefix
                or not isinstance(argv[-3], str)
                or not re.fullmatch(
                    r"cotcodec-supermemory-doctor-[0-9a-f]{16}:/state:rw",
                    argv[-3],
                )
                or argv[-2:] != [image_id, phase]
            ):
                raise EvidenceError("Supermemory contained execution argv drifted")
            if volume_arg is None:
                volume_arg = argv[-3]
            elif argv[-3] != volume_arg:
                raise EvidenceError("Supermemory run volume changed across phases")
            phase_argv.append(argv)
        assert volume_arg is not None
        run_volumes.append(volume_arg)
        projections.append(projection)
        execution_identities.append(_sha256(_canonical_json(phase_argv)))
    if (
        projections[0] != projections[1]
        or len(set(execution_identities)) != 2
        or len(set(run_volumes)) != 2
    ):
        raise EvidenceError("Supermemory repetitions are not distinct and equal")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "stable_projection": projections[0],
        "execution_identities": execution_identities,
    }


def validate_graphiti_container_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the exact Graphiti/FalkorDBLite container blocker."""

    if set(files) != GRAPHITI_REQUIRED_FILES:
        raise EvidenceError("Graphiti evidence file roster drifted")
    if _sha256(files["registered-experiment.yaml"]) != GRAPHITI_EXPERIMENT_SHA256:
        raise EvidenceError("Graphiti registered experiment drifted")

    manifest = _decode_json(files["manifest.json"], "Graphiti manifest")
    manifest_without_root = dict(manifest)
    manifest_root = manifest_without_root.pop("manifest_sha256", None)
    expected_manifest_root = _sha256(
        json.dumps(
            manifest_without_root,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    )
    expected_runs = [
        {"path": f"run-{index}.json", "sha256": _sha256(files[f"run-{index}.json"])}
        for index in (1, 2)
    ]
    if (
        manifest.get("schema_version") != "1.0"
        or manifest.get("status") != GRAPHITI_STATUS
        or manifest_root != expected_manifest_root
        or manifest.get("image_inspect_sha256")
        != _sha256(files["image-inspect.json"])
        or manifest.get("module_architecture_sha256")
        != _sha256(files["module-architecture.json"])
        or manifest.get("report_sha256") != _sha256(files["report.json"])
        or manifest.get("runs") != expected_runs
    ):
        raise EvidenceError("Graphiti manifest or child receipt drifted")

    module = _decode_json(
        files["module-architecture.json"], "Graphiti module architecture"
    )
    expected_module = {
        "falkordb.so": {
            "e_machine": 62,
            "elf_class": 2,
            "elf_data": 1,
            "sha256": (
                "47885e2da788c3fb822b9bd4c182a9694d67286a7fd8fe18c33e3c1a0d05636b"
            ),
            "size": 51_475_528,
        },
        "redis-server": {
            "e_machine": 183,
            "elf_class": 2,
            "elf_data": 1,
            "sha256": (
                "a98cb3fd27705c7e33b0a2db3c8647bcc33ef230200bc5670bf792ddf75e9f9e"
            ),
            "size": 13_897_584,
        },
    }
    if module != expected_module:
        raise EvidenceError("Graphiti module architecture drifted")

    inspect = _decode_json(files["image-inspect.json"], "Graphiti image inspect")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        inspect.get("Id") != GRAPHITI_IMAGE_ID
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != GRAPHITI_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != GRAPHITI_SOURCE_ARCHIVE_SHA256
        or labels.get("org.cotcodec.memory-lifecycle-adapter")
        != "graphiti-explicit-triplet-lifecycle-v1"
        or labels.get("org.cotcodec.graphiti-lifecycle-doctor-sha256")
        != GRAPHITI_RUNNER_SHA256
        or labels.get("org.cotcodec.graphiti-lifecycle-experiment-sha256")
        != GRAPHITI_EXPERIMENT_SHA256
        or labels.get("org.cotcodec.scientific-result") != "false"
    ):
        raise EvidenceError("Graphiti image identity drifted")

    expected_checks = {
        "adapter_exact": True,
        "distinct_container_receipts": True,
        "experiment_exact": True,
        "failure_is_native_server_start": True,
        "falkordb_module_is_x86_64": True,
        "graphiti_revision_exact": True,
        "image_architecture_arm64": True,
        "image_id_immutable": True,
        "redis_server_is_aarch64": True,
        "runner_exact": True,
        "runtime_network_none": True,
        "scientific_result_false": True,
        "source_archive_exact": True,
        "two_clean_failures_reproduced": True,
    }
    report = _decode_json(files["report.json"], "Graphiti report")
    if (
        report.get("schema_version") != "1.0"
        or report.get("status") != GRAPHITI_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_admission") != "forbidden"
        or report.get("image_id") != GRAPHITI_IMAGE_ID
        or report.get("checks") != expected_checks
        or report.get("module_architecture") != module
        or report.get("implication")
        != (
            "FalkorDBLite 0.10.0 built ARM64 Redis binaries but packaged an x86-64 "
            "Falkor module; the contained native Graphiti lifecycle cannot start."
        )
    ):
        raise EvidenceError("Graphiti blocker semantics drifted")

    expected_create_argv = [
        "docker",
        "create",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--cpus",
        "2",
        "--memory",
        "2560m",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/state:rw,noexec,nosuid,nodev,size=1g,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/outputs:rw,noexec,nosuid,nodev,size=64m,uid=65532,gid=65532,mode=0700",
        GRAPHITI_IMAGE_ID,
        "--state-root",
        "/state/run",
        "--output-dir",
        "/outputs",
    ]
    execution_identities: list[str] = []
    for index in (1, 2):
        run = _decode_json(files[f"run-{index}.json"], f"Graphiti run {index}")
        receipt = run.get("container_receipt")
        if not isinstance(receipt, dict):
            raise EvidenceError("Graphiti container receipt is missing")
        container_id = receipt.get("container_id")
        state = receipt.get("state")
        host = receipt.get("host_config")
        if (
            run.get("index") != index
            or run.get("create_argv") != expected_create_argv
            or not isinstance(container_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", container_id)
            or run.get("start_argv")
            != ["docker", "start", "--attach", container_id]
            or run.get("inspect_argv")
            != ["docker", "container", "inspect", container_id]
            or run.get("remove_argv")
            != ["docker", "container", "rm", container_id]
            or run.get("exit_code") != 1
            or run.get("stdout") != ""
            or "The redis-server process failed to start" not in run.get("stderr", "")
            or receipt.get("image_id") != GRAPHITI_IMAGE_ID
            or receipt.get("mounts") != []
            or not isinstance(receipt.get("created_at"), str)
            or not receipt["created_at"]
            or host
            != {
                "auto_remove": False,
                "cap_drop": ["ALL"],
                "memory": 2_684_354_560,
                "nano_cpus": 2_000_000_000,
                "network_mode": "none",
                "pids_limit": 256,
                "readonly_rootfs": True,
                "security_opt": ["no-new-privileges"],
                "tmpfs": {
                    "/outputs": (
                        "rw,noexec,nosuid,nodev,size=64m,uid=65532,gid=65532,mode=0700"
                    ),
                    "/state": (
                        "rw,noexec,nosuid,nodev,size=1g,uid=65532,gid=65532,mode=0700"
                    ),
                    "/tmp": (
                        "rw,noexec,nosuid,nodev,size=256m,uid=65532,gid=65532,mode=0700"
                    ),
                },
            }
            or not isinstance(state, dict)
            or state.get("error") != ""
            or state.get("exit_code") != 1
            or state.get("running") is not False
            or state.get("status") != "exited"
            or not isinstance(state.get("started_at"), str)
            or not state["started_at"]
            or not isinstance(state.get("finished_at"), str)
            or not state["finished_at"]
        ):
            raise EvidenceError("Graphiti contained failure receipt drifted")
        execution_identities.append(_sha256(_canonical_json(receipt)))
    if len(set(execution_identities)) != 2:
        raise EvidenceError("Graphiti repetitions lack distinct execution receipts")
    return {
        "manifest_root": manifest_root,
        "image_id": GRAPHITI_IMAGE_ID,
        "module_architecture": module,
        "execution_identities": execution_identities,
    }


def validate_magic_context_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the complete Magic Context boundary/negative contract."""

    if set(files) != MAGIC_CONTEXT_REQUIRED_FILES:
        raise EvidenceError("Magic Context evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Magic Context manifest")
    expected_artifacts = MAGIC_CONTEXT_REQUIRED_FILES - {"manifest.json"}
    artifacts = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != MAGIC_CONTEXT_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("Magic Context manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        if artifacts[name] != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"Magic Context artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("Magic Context manifest root drifted")

    report = _decode_json(files["report.json"], "Magic Context report")
    source = _decode_json(files["source-receipt.json"], "Magic Context source receipt")
    inspect = _decode_json(files["image-inspect.json"], "Magic Context image inspect")
    expected_findings = {
        "chronological_prompt_paging_supported": True,
        "exact_raw_json_recovery_supported": False,
        "host_raw_storage_required": True,
        "native_secure_purge_supported": False,
        "plaintext_residue_reproduced": True,
        "same_session_id_cross_harness_alias_reproduced": True,
        "semantic_item_paging_supported": False,
        "supported_projection_restart_stable": True,
    }
    expected_admission = {
        "chronological_prompt_paging_boundary": "supported-cpu-conformance-only",
        "cluster_confirmation": "not-run",
        "portable_lifecycle": "blocked",
        "semantic_memory_h100": "forbidden-for-this-mechanism",
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "magic-context-paging-falsification-v1"
        or report.get("status") != MAGIC_CONTEXT_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("findings") != expected_findings
        or report.get("admission") != expected_admission
    ):
        raise EvidenceError("Magic Context result semantics drifted")
    if (
        source.get("repository") != "https://github.com/cortexkit/magic-context"
        or source.get("revision") != MAGIC_CONTEXT_REVISION
        or source.get("tree") != "f420beb3be130544534ff7a9778a49e92fa0ed75"
        or source.get("git_archive_tar_sha256")
        != "8eb4b81542b157d55fb4c43cea523fc8297a6b360f8a90feff2a8737b8d40080"
        or source.get("bun_lock_sha256")
        != "8e8bc07020c1ad17a5a560740b8ec5f108a205b9c58cce166340b99251b9cb5f"
        or source.get("dockerfile_sha256") != MAGIC_CONTEXT_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != MAGIC_CONTEXT_DOCTOR_SHA256
        or source.get("worktree_clean") is not True
    ):
        raise EvidenceError("Magic Context source receipt drifted")
    if _sha256(files["experiment.yaml"]) != MAGIC_CONTEXT_EXPERIMENT_SHA256:
        raise EvidenceError("Magic Context registered experiment drifted")
    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != MAGIC_CONTEXT_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != source["git_archive_tar_sha256"]
    ):
        raise EvidenceError("Magic Context image receipt drifted")

    projections: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    for run in (1, 2):
        prefix = f"run-{run}"
        prepare = _decode_json(files[f"{prefix}/prepare.json"], "Magic Context prepare")
        restart = _decode_json(files[f"{prefix}/restart.json"], "Magic Context restart")
        alias = _decode_json(files[f"{prefix}/alias.json"], "Magic Context alias")
        purge = _decode_json(files[f"{prefix}/purge.json"], "Magic Context purge")
        projection = _decode_json(
            files[f"{prefix}/stable-projection.json"], "Magic Context stable projection"
        )
        if (
            prepare.get("phase") != "prepare"
            or restart.get("phase") != "restart"
            or alias.get("phase") != "alias"
            or purge.get("phase") != "purge"
            or prepare.get("model_calls") != 0
            or prepare.get("network_calls") != 0
            or prepare.get("projection_sha256") != restart.get("projection_sha256")
            or restart.get("host_storage_required") is not True
            or restart.get("supported_projection_not_raw_json") is not True
            or alias.get("same_session_id_cross_harness_alias_reproduced") is not True
            or alias.get("portable_lifecycle_admission") != "blocked"
            or purge.get("plugin_logical_session_a_rows") != 0
            or purge.get("session_b_rows") != 1
            or purge.get("native_secure_purge_supported") is not False
            or purge.get("physical_zero_residue") is not False
            or purge.get("host_row_deletion_makes_expansion_unrecoverable") is not True
            or not purge.get("physical_hits")
            or projection.get("alias") != alias
            or projection.get("expansion") != prepare.get("projection", {}).get("expansion")
            or projection.get("paging") != prepare.get("projection", {}).get("paging")
            or projection.get("purge", {}).get("physical_hits") != purge.get("physical_hits")
        ):
            raise EvidenceError("Magic Context run semantics drifted")
        if _sha256(_canonical_json(projection)) != report.get("stable_projection_sha256"):
            raise EvidenceError("Magic Context stable projection root drifted")
        phase_argv = []
        for phase in ("prepare", "restart", "alias", "purge"):
            argv = json.loads(files[f"{prefix}/{phase}.argv.json"])
            if (
                not isinstance(argv, list)
                or "--network" not in argv
                or argv[argv.index("--network") + 1] != "none"
                or "--read-only" not in argv
                or "--cap-drop" not in argv
                or argv[argv.index("--cap-drop") + 1] != "ALL"
                or "no-new-privileges" not in argv
                or argv[-2:] != [image_id, phase]
            ):
                raise EvidenceError("Magic Context contained execution argv drifted")
            phase_argv.append(argv)
        projections.append(projection)
        execution_identities.append(_sha256(_canonical_json(phase_argv)))
    if projections[0] != projections[1] or len(set(execution_identities)) != 2:
        raise EvidenceError("Magic Context clean-state repetitions are not distinct and equal")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "stable_projection": projections[0],
        "execution_identities": execution_identities,
    }


def validate_gaama_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the contained GAAMA matched-component contract."""

    if set(files) != GAAMA_REQUIRED_FILES:
        raise EvidenceError("GAAMA evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "GAAMA manifest")
    expected_artifacts = GAAMA_REQUIRED_FILES - {"manifest.json"}
    artifacts = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != GAAMA_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("GAAMA manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        if artifacts[name] != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"GAAMA artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("GAAMA manifest root drifted")

    report = _decode_json(files["report.json"], "GAAMA report")
    source = _decode_json(files["source-receipt.json"], "GAAMA source receipt")
    inspect = _decode_json(files["image-inspect.json"], "GAAMA image inspect")
    if (
        report.get("schema_version") != 1
        or report.get("study") != "gaama-matched-graph-component-doctor-v1"
        or report.get("status") != GAAMA_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("admission")
        != {"h100": "blocked", "natural_heldout_component": "not-run"}
    ):
        raise EvidenceError("GAAMA outer result semantics drifted")
    if (
        source.get("repository") != "https://github.com/swarna-kpaul/gaama"
        or source.get("revision") != GAAMA_REVISION
        or source.get("tree") != "0227970b58617696afd53d27f920a10e3c401ece"
        or source.get("git_archive_tar_sha256")
        != "d9aec03fe4a268bf091dc2c419e270720e5cfffcdcbdfdd9e43b62bec00a4e9d"
        or source.get("dockerfile_sha256") != GAAMA_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != GAAMA_DOCTOR_SHA256
        or source.get("component_sha256")
        != "01ddd1feba8d033777d8f56ac19932faac3ae52e118302765919bbd0cd7ffa2b"
        or source.get("worktree_clean") is not True
    ):
        raise EvidenceError("GAAMA source receipt drifted")
    if _sha256(files["experiment.yaml"]) != GAAMA_EXPERIMENT_SHA256:
        raise EvidenceError("GAAMA registered experiment drifted")

    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != GAAMA_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != source["git_archive_tar_sha256"]
    ):
        raise EvidenceError("GAAMA image receipt drifted")

    component_reports: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    for run in (1, 2):
        component = _decode_json(files[f"run-{run}/report.json"], "GAAMA component")
        try:
            argv = json.loads(files[f"run-{run}/argv.json"])
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise EvidenceError("GAAMA argv is not valid JSON") from exc
        rows = component.get("rows")
        expected_hash = _sha256(
            _canonical_json(
                {key: value for key, value in component.items() if key != "report_sha256"}
            )
        )
        if (
            component.get("report_sha256") != expected_hash
            or component.get("status") != GAAMA_STATUS
            or component.get("case_count") != 24
            or component.get("model_calls") != 0
            or component.get("embedding_calls") != 0
            or component.get("network_calls") != 0
            or component.get("candidate_pool_matched") is not True
            or component.get("ppr_weight_zero_equal_flat") is not True
            or component.get("true_graph_hits") != 24
            or component.get("flat_hits") != 0
            or component.get("shuffled_graph_hits") != 0
            or component.get("hub_dampening_noop_after_row_normalization") is not True
            or component.get("cross_task_edges") != 0
            or not isinstance(rows, list)
            or len(rows) != 24
            or any(
                len(row.get("candidate_ids", [])) != 5
                or row.get("flat") != row.get("ppr_weight_zero")
                or row.get("flat_hit") is not False
                or row.get("true_hit") is not True
                or row.get("shuffled_hit") is not False
                for row in rows
            )
        ):
            raise EvidenceError("GAAMA component semantics drifted")
        if (
            not isinstance(argv, list)
            or "--network" not in argv
            or argv[argv.index("--network") + 1] != "none"
            or "--read-only" not in argv
            or "--cap-drop" not in argv
            or argv[argv.index("--cap-drop") + 1] != "ALL"
            or "no-new-privileges" not in argv
            or image_id not in argv
        ):
            raise EvidenceError("GAAMA execution containment drifted")
        component_reports.append(component)
        execution_identities.append(_sha256(_canonical_json(argv)))
    if component_reports[0] != component_reports[1] or len(set(execution_identities)) != 2:
        raise EvidenceError("GAAMA clean repetitions are not distinct and equal")
    summary = {key: value for key, value in component_reports[0].items() if key != "rows"}
    if report.get("component") != summary:
        raise EvidenceError("GAAMA outer component summary drifted")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "component_summary": summary,
        "execution_identities": execution_identities,
    }


def _natural_arm_summary(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    metrics = (
        "any_at_5",
        "all_at_5",
        "any_at_10",
        "all_at_10",
        "any_at_20",
        "all_at_20",
    )
    return {
        "questions": len(rows),
        **{
            metric: sum(float(row["metrics"][metric]) for row in rows) / len(rows)
            for metric in metrics
        },
    }


def _natural_paired(
    left: list[dict[str, Any]], right: list[dict[str, Any]]
) -> dict[str, list[float]]:
    right_by_id = {row["question_id"]: row for row in right}
    paired: dict[str, list[float]] = defaultdict(list)
    if set(right_by_id) != {row["question_id"] for row in left}:
        raise EvidenceError("GAAMA natural paired roster drifted")
    for row in left:
        paired[row["sample_id"]].append(
            float(row["metrics"]["all_at_10"])
            - float(right_by_id[row["question_id"]]["metrics"]["all_at_10"])
        )
    return dict(paired)


def _natural_paired_mean_controls(
    treated: list[dict[str, Any]],
    controls: tuple[list[dict[str, Any]], ...],
) -> dict[str, list[float]]:
    control_maps = [
        {row["question_id"]: row for row in control} for control in controls
    ]
    treated_ids = {row["question_id"] for row in treated}
    if not controls or any(set(control) != treated_ids for control in control_maps):
        raise EvidenceError("GAAMA natural shuffled-control roster drifted")
    paired: dict[str, list[float]] = defaultdict(list)
    for row in treated:
        question_id = row["question_id"]
        control_mean = sum(
            float(control[question_id]["metrics"]["all_at_10"])
            for control in control_maps
        ) / len(control_maps)
        paired[row["sample_id"]].append(
            float(row["metrics"]["all_at_10"]) - control_mean
        )
    return dict(paired)


@lru_cache(maxsize=2)
def _rerun_gaama_natural(dataset_bytes: bytes) -> dict[str, Any]:
    from harness.memory_trials.gaama_natural import run_natural_holdout

    with tempfile.TemporaryDirectory(prefix="gaama-natural-evidence-") as directory:
        dataset = Path(directory) / "locomo10.json"
        dataset.write_bytes(dataset_bytes)
        return run_natural_holdout(dataset)


def _natural_clustered_interval(paired: dict[str, list[float]]) -> list[float]:
    groups = sorted(paired)
    group_means = {
        group: sum(paired[group]) / len(paired[group]) for group in groups
    }
    generator = random.Random(20260814)
    values: list[float] = []
    for _ in range(10_000):
        sampled = [generator.choice(groups) for _ in groups]
        values.append(sum(group_means[group] for group in sampled) / len(sampled))
    values.sort()
    return [values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]]


def _natural_cluster_mean(paired: dict[str, list[float]]) -> float:
    group_means = [sum(values) / len(values) for values in paired.values()]
    return sum(group_means) / len(group_means)


def _natural_sign_p(paired: dict[str, list[float]]) -> float:
    group_means = [sum(values) / len(values) for _, values in sorted(paired.items())]
    observed = sum(group_means) / len(group_means)
    total = 1 << len(group_means)
    exceed = 0
    for mask in range(total):
        value = sum(
            score if mask & (1 << index) else -score
            for index, score in enumerate(group_means)
        ) / len(group_means)
        if value >= observed - 1e-15:
            exceed += 1
    return exceed / total


def _natural_metrics_from_top20(
    top_20: list[str], evidence_ids: list[str]
) -> dict[str, float]:
    evidence = set(evidence_ids)
    return {
        "any_at_5": float(bool(evidence & set(top_20[:5]))),
        "all_at_5": float(evidence <= set(top_20[:5])),
        "any_at_10": float(bool(evidence & set(top_20[:10]))),
        "all_at_10": float(evidence <= set(top_20[:10])),
        "any_at_20": float(bool(evidence & set(top_20[:20]))),
        "all_at_20": float(evidence <= set(top_20[:20])),
    }


def _validate_natural_rows(
    rows: Any,
    *,
    expected_count: int,
    sample_ids: set[str],
    owner: str,
) -> list[dict[str, Any]]:
    metric_names = {
        "all_at_10",
        "all_at_20",
        "all_at_5",
        "any_at_10",
        "any_at_20",
        "any_at_5",
    }
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise EvidenceError(f"GAAMA natural {owner} row count drifted")
    question_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise EvidenceError(f"GAAMA natural {owner} row semantics drifted")
        top_20 = row.get("top_20")
        evidence_ids = row.get("evidence_ids")
        if (
            not isinstance(top_20, list)
            or not all(isinstance(value, str) for value in top_20)
            or not isinstance(evidence_ids, list)
            or not all(isinstance(value, str) for value in evidence_ids)
        ):
            raise EvidenceError(f"GAAMA natural {owner} ranking fields drifted")
        expected_metrics = _natural_metrics_from_top20(top_20, evidence_ids)
        if (
            row.get("sample_id") not in sample_ids
            or row.get("category") not in {1, 2, 3, 4}
            or not isinstance(row.get("question_id"), str)
            or not row["question_id"].startswith(f"{row['sample_id']}:")
            or set(row.get("metrics", {})) != metric_names
            or not all(
                isinstance(value, (int, float)) and math.isfinite(float(value))
                for value in row["metrics"].values()
            )
            or len(top_20) != 20
            or len(set(top_20)) != 20
            or not evidence_ids
            or row.get("metrics") != expected_metrics
        ):
            raise EvidenceError(f"GAAMA natural {owner} row semantics drifted")
        question_ids.add(row["question_id"])
    if len(question_ids) != expected_count:
        raise EvidenceError(f"GAAMA natural {owner} question IDs are not unique")
    return rows


def validate_gaama_natural_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the natural held-out GAAMA graph retrieval result."""

    if set(files) != GAAMA_NATURAL_REQUIRED_FILES:
        raise EvidenceError("GAAMA natural evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "GAAMA natural manifest")
    artifacts = manifest.get("files")
    expected_artifacts = GAAMA_NATURAL_REQUIRED_FILES - {"manifest.json"}
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != GAAMA_NATURAL_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("GAAMA natural manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        if artifacts[name] != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"GAAMA natural artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("GAAMA natural manifest root drifted")

    report = _decode_json(files["report.json"], "GAAMA natural report")
    source = _decode_json(files["source-receipt.json"], "GAAMA natural source")
    inspect = _decode_json(files["image-inspect.json"], "GAAMA natural image")
    dataset_bytes = files["source/locomo10.json"]
    if (
        report.get("schema_version") != 1
        or report.get("study") != "gaama-natural-heldout-graph-retrieval-v1"
        or report.get("status") != GAAMA_NATURAL_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("admission")
        != {
            "h100": "eligible-for-separate-design-review",
            "natural_heldout_component": "pass",
        }
    ):
        raise EvidenceError("GAAMA natural outer report drifted")
    if (
        source.get("repository") != "https://github.com/swarna-kpaul/gaama"
        or source.get("revision") != GAAMA_REVISION
        or source.get("tree") != "0227970b58617696afd53d27f920a10e3c401ece"
        or source.get("git_archive_tar_sha256")
        != "d9aec03fe4a268bf091dc2c419e270720e5cfffcdcbdfdd9e43b62bec00a4e9d"
        or source.get("locomo10_sha256")
        != "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
        or source.get("dockerfile_sha256") != GAAMA_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != GAAMA_NATURAL_DOCTOR_SHA256
        or source.get("natural_module_sha256") != GAAMA_NATURAL_MODULE_SHA256
        or source.get("component_sha256")
        != "01ddd1feba8d033777d8f56ac19932faac3ae52e118302765919bbd0cd7ffa2b"
        or source.get("worktree_clean") is not True
    ):
        raise EvidenceError("GAAMA natural source receipt drifted")
    if _sha256(dataset_bytes) != source["locomo10_sha256"]:
        raise EvidenceError("GAAMA natural embedded dataset drifted")
    local_code = {
        "natural_module_sha256": PROJECT_ROOT
        / "harness/memory_trials/gaama_natural.py",
        "component_sha256": PROJECT_ROOT
        / "harness/memory_trials/gaama_component.py",
        "doctor_sha256": PROJECT_ROOT
        / "infra/memory-baselines/gaama-natural/doctor.py",
        "dockerfile_sha256": PROJECT_ROOT
        / "infra/memory-baselines/gaama-natural/Dockerfile",
    }
    for field, path in local_code.items():
        if path.is_symlink() or not path.is_file():
            raise EvidenceError(f"GAAMA natural local verifier input is invalid: {field}")
        if _sha256(path.read_bytes()) != source[field]:
            raise EvidenceError(f"GAAMA natural local verifier code drifted: {field}")
    if _sha256(files["experiment.yaml"]) != GAAMA_NATURAL_EXPERIMENT_SHA256:
        raise EvidenceError("GAAMA natural registered experiment drifted")

    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != GAAMA_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != source["git_archive_tar_sha256"]
    ):
        raise EvidenceError("GAAMA natural image receipt drifted")

    weights = [0.0, 0.05, 0.1, 0.25, 0.5, 1.0]
    dev_samples = {"conv-26", "conv-30", "conv-41"}
    test_samples = {"conv-42", "conv-43", "conv-44", "conv-47", "conv-48", "conv-49", "conv-50"}
    test_arms = {
        "flat",
        "ppr_weight_zero",
        "true_graph",
        "shuffled_graph_seed_42",
        "shuffled_graph_seed_43",
        "shuffled_graph_seed_44",
    }
    natural_reports: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    independently_recomputed = _rerun_gaama_natural(dataset_bytes)
    for run in (1, 2):
        natural = _decode_json(files[f"run-{run}/report.json"], "GAAMA natural result")
        try:
            argv = json.loads(files[f"run-{run}/argv.json"])
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise EvidenceError("GAAMA natural argv is not valid JSON") from exc
        expected_hash = _sha256(
            _canonical_json(
                {key: value for key, value in natural.items() if key != "report_sha256"}
            )
        )
        dev_rows = natural.get("dev_rows")
        rows = natural.get("rows")
        if (
            natural.get("report_sha256") != expected_hash
            or natural.get("status") != GAAMA_NATURAL_STATUS
            or natural.get("dataset_sha256") != source["locomo10_sha256"]
            or natural.get("dev_sample_ids") != ["conv-26", "conv-30", "conv-41"]
            or natural.get("test_sample_ids")
            != ["conv-42", "conv-43", "conv-44", "conv-47", "conv-48", "conv-49", "conv-50"]
            or natural.get("dev_questions") != 382
            or natural.get("test_questions") != 1146
            or natural.get("dialogue_nodes") != 5882
            or natural.get("primary_metric") != "evidence_recall_all_at_10"
            or natural.get("model_calls") != 0
            or natural.get("embedding_calls") != 0
            or natural.get("network_calls") != 0
            or natural.get("scientific_result") is not False
            or natural.get("publication_ready") is not False
            or not isinstance(dev_rows, dict)
            or set(dev_rows) != {str(weight) for weight in weights}
            or not isinstance(rows, dict)
            or set(rows) != test_arms
        ):
            raise EvidenceError("GAAMA natural result identity drifted")
        validated_dev = {
            str(weight): _validate_natural_rows(
                dev_rows[str(weight)],
                expected_count=382,
                sample_ids=dev_samples,
                owner=f"dev-{weight}",
            )
            for weight in weights
        }
        validated_test = {
            arm: _validate_natural_rows(
                rows[arm],
                expected_count=1146,
                sample_ids=test_samples,
                owner=arm,
            )
            for arm in test_arms
        }
        dev_rosters = {
            tuple(row["question_id"] for row in arm_rows)
            for arm_rows in validated_dev.values()
        }
        test_rosters = {
            tuple(row["question_id"] for row in arm_rows)
            for arm_rows in validated_test.values()
        }
        dev_scores = {
            str(weight): _natural_arm_summary(validated_dev[str(weight)])["all_at_10"]
            for weight in weights
        }
        selected = min(weights, key=lambda weight: (-float(dev_scores[str(weight)]), weight))
        summaries = {
            arm: _natural_arm_summary(arm_rows)
            for arm, arm_rows in validated_test.items()
        }
        paired = _natural_paired(validated_test["true_graph"], validated_test["flat"])
        shuffled_paired = _natural_paired_mean_controls(
            validated_test["true_graph"],
            tuple(
                validated_test[f"shuffled_graph_seed_{seed}"]
                for seed in (42, 43, 44)
            ),
        )
        true_score = float(summaries["true_graph"]["all_at_10"])
        flat_score = float(summaries["flat"]["all_at_10"])
        mean_shuffled = sum(
            float(summaries[f"shuffled_graph_seed_{seed}"]["all_at_10"])
            for seed in (42, 43, 44)
        ) / 3
        primary = {
            "true_minus_flat": _natural_cluster_mean(paired),
            "clustered_bootstrap_95_ci": _natural_clustered_interval(paired),
            "conversation_sign_randomization_p_one_sided": _natural_sign_p(paired),
            "true_minus_mean_shuffled": _natural_cluster_mean(shuffled_paired),
            "true_minus_mean_shuffled_clustered_bootstrap_95_ci": (
                _natural_clustered_interval(shuffled_paired)
            ),
            "true_minus_mean_shuffled_sign_randomization_p_one_sided": (
                _natural_sign_p(shuffled_paired)
            ),
            "pooled_question_true_minus_flat": true_score - flat_score,
            "pooled_question_true_minus_mean_shuffled": true_score - mean_shuffled,
        }
        graph_gates = {
            "selected_nonzero_weight": selected > 0,
            "true_minus_flat_at_least_one_point": primary["true_minus_flat"] >= 0.01,
            "clustered_ci_excludes_zero": primary["clustered_bootstrap_95_ci"][0] > 0,
            "true_minus_mean_shuffled_at_least_one_point": primary[
                "true_minus_mean_shuffled"
            ]
            >= 0.01,
            "one_sided_sign_randomization_below_0_05": primary[
                "conversation_sign_randomization_p_one_sided"
            ]
            < 0.05,
            "shuffled_clustered_ci_excludes_zero": primary[
                "true_minus_mean_shuffled_clustered_bootstrap_95_ci"
            ][0]
            > 0,
            "shuffled_one_sided_sign_randomization_below_0_05": primary[
                "true_minus_mean_shuffled_sign_randomization_p_one_sided"
            ]
            < 0.05,
        }
        if (
            len(dev_rosters) != 1
            or len(test_rosters) != 1
            or natural.get("dev_weight_scores") != dev_scores
            or natural.get("selected_ppr_weight") != selected
            or natural.get("arm_summaries") != summaries
            or natural.get("primary_comparison") != primary
            or natural.get("graph_gates") != graph_gates
            or not all(graph_gates.values())
            or not all(natural.get("integrity_gates", {}).values())
            or validated_test["flat"] != validated_test["ppr_weight_zero"]
            or natural != independently_recomputed
            or natural.get("h100_admission") != "eligible-for-separate-design-review"
        ):
            raise EvidenceError("GAAMA natural computed semantics drifted")
        if (
            not isinstance(argv, list)
            or "--network" not in argv
            or argv[argv.index("--network") + 1] != "none"
            or "--read-only" not in argv
            or "--cap-drop" not in argv
            or argv[argv.index("--cap-drop") + 1] != "ALL"
            or "no-new-privileges" not in argv
            or "--pids-limit" not in argv
            or argv[argv.index("--pids-limit") + 1] != "256"
            or argv[-1] != image_id
        ):
            raise EvidenceError("GAAMA natural execution containment drifted")
        natural_reports.append(natural)
        execution_identities.append(_sha256(_canonical_json(argv)))
    if natural_reports[0] != natural_reports[1] or len(set(execution_identities)) != 2:
        raise EvidenceError("GAAMA natural clean repetitions are not distinct and equal")
    first = natural_reports[0]
    expected_outcome = {
        "selected_ppr_weight": first["selected_ppr_weight"],
        "test_questions": first["test_questions"],
        "arm_summaries": first["arm_summaries"],
        "primary_comparison": first["primary_comparison"],
        "integrity_gates": first["integrity_gates"],
        "graph_gates": first["graph_gates"],
    }
    if (
        report.get("natural_report_sha256") != first["report_sha256"]
        or report.get("outcome") != expected_outcome
    ):
        raise EvidenceError("GAAMA natural outer outcome drifted")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "outcome": expected_outcome,
        "execution_identities": execution_identities,
    }


def validate_holographic_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the Hermes Holographic native lifecycle negative."""

    if set(files) != HOLOGRAPHIC_REQUIRED_FILES:
        raise EvidenceError("Holographic evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Holographic manifest")
    expected_artifacts = HOLOGRAPHIC_REQUIRED_FILES - {"manifest.json"}
    artifacts = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != HOLOGRAPHIC_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("Holographic manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        if artifacts[name] != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"Holographic artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("Holographic manifest root drifted")

    report = _decode_json(files["report.json"], "Holographic report")
    source = _decode_json(files["source-receipt.json"], "Holographic source receipt")
    inspect = _decode_json(files["image-inspect.json"], "Holographic image inspect")
    expected_findings = {
        "duplicate_add_idempotence_supported": True,
        "native_session_purge_supported": False,
        "native_sqlite_fts_restart_supported": True,
        "physical_zero_residue_after_logical_delete": True,
        "plaintext_residue_reproduced": False,
        "session_scoped_isolation_supported": False,
        "update_and_feedback_persist": True,
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "hermes-holographic-lifecycle-falsification-v1"
        or report.get("status") != HOLOGRAPHIC_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("findings") != expected_findings
        or report.get("admission")
        != {
            "cluster_confirmation": "not-run",
            "memory_lifecycle_h100": "forbidden-for-this-revision",
            "provider_contract": "local-negative-only",
        }
    ):
        raise EvidenceError("Holographic result semantics drifted")
    if (
        source.get("repository") != "https://github.com/NousResearch/hermes-agent"
        or source.get("revision") != HOLOGRAPHIC_REVISION
        or source.get("tree") != "963eb136bfb21fd0b296a40529cbb3575c610874"
        or source.get("git_archive_tar_sha256")
        != "2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514"
        or source.get("dockerfile_sha256") != HOLOGRAPHIC_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != HOLOGRAPHIC_DOCTOR_SHA256
        or source.get("store_sha256")
        != "696dc3f8e683362d857e38e87fd7bd8dcc491cfa8f25ba31818e041d91695e74"
        or source.get("worktree_clean") is not True
    ):
        raise EvidenceError("Holographic source receipt drifted")
    if _sha256(files["experiment.yaml"]) != HOLOGRAPHIC_EXPERIMENT_SHA256:
        raise EvidenceError("Holographic registered experiment drifted")
    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != HOLOGRAPHIC_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != source["git_archive_tar_sha256"]
    ):
        raise EvidenceError("Holographic image receipt drifted")

    projections: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    for run in (1, 2):
        prefix = f"run-{run}"
        prepare = _decode_json(files[f"{prefix}/prepare.json"], "Holographic prepare")
        restart = _decode_json(files[f"{prefix}/restart.json"], "Holographic restart")
        purge = _decode_json(files[f"{prefix}/purge.json"], "Holographic purge")
        projection = _decode_json(
            files[f"{prefix}/stable-projection.json"], "Holographic projection"
        )
        if (
            prepare.get("phase") != "prepare"
            or restart.get("phase") != "restart"
            or purge.get("phase") != "purge"
            or prepare.get("duplicate_add_same_id") is not True
            or prepare.get("snapshot") != restart.get("snapshot")
            or restart.get("restart_persistence_supported") is not True
            or restart.get("session_a_visible_from_fresh_session_b") is not True
            or restart.get("session_scoped_isolation_supported") is not False
            or purge.get("logical_rows_after_restart") != 0
            or purge.get("native_session_purge_supported") is not False
            or purge.get("physical_zero_residue_after_logical_delete") is not True
            or purge.get("physical_hits") != []
            or projection.get("snapshot") != prepare.get("snapshot")
        ):
            raise EvidenceError("Holographic lifecycle semantics drifted")
        phase_argv: list[Any] = []
        for phase in ("prepare", "restart", "purge"):
            try:
                argv = json.loads(files[f"{prefix}/{phase}.argv.json"])
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise EvidenceError("Holographic argv is not valid JSON") from exc
            if (
                not isinstance(argv, list)
                or "--network" not in argv
                or argv[argv.index("--network") + 1] != "none"
                or "--read-only" not in argv
                or "--cap-drop" not in argv
                or argv[argv.index("--cap-drop") + 1] != "ALL"
                or "no-new-privileges" not in argv
                or image_id not in argv
            ):
                raise EvidenceError("Holographic execution containment drifted")
            phase_argv.append(argv)
        projections.append(projection)
        execution_identities.append(_sha256(_canonical_json(phase_argv)))
    if projections[0] != projections[1] or len(set(execution_identities)) != 2:
        raise EvidenceError("Holographic clean repetitions are not distinct and equal")
    if report.get("stable_projection_sha256") != _sha256(_canonical_json(projections[0])):
        raise EvidenceError("Holographic stable projection receipt drifted")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "stable_projection": projections[0],
        "execution_identities": execution_identities,
    }


def validate_byterover_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the Hermes ByteRover native offline negative."""

    if set(files) != BYTEROVER_REQUIRED_FILES:
        raise EvidenceError("ByteRover evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "ByteRover manifest")
    expected_artifacts = BYTEROVER_REQUIRED_FILES - {"manifest.json"}
    artifacts = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != BYTEROVER_STATUS
        or not isinstance(artifacts, dict)
        or set(artifacts) != expected_artifacts
    ):
        raise EvidenceError("ByteRover manifest identity or roster drifted")
    for name in sorted(expected_artifacts):
        if artifacts[name] != {"bytes": len(files[name]), "sha256": _sha256(files[name])}:
            raise EvidenceError(f"ByteRover artifact receipt drifted: {name}")
    if manifest.get("root_sha256") != _sha256(_canonical_json(artifacts)):
        raise EvidenceError("ByteRover manifest root drifted")

    report = _decode_json(files["report.json"], "ByteRover report")
    source = _decode_json(files["source-receipt.json"], "ByteRover source receipt")
    inspect = _decode_json(files["image-inspect.json"], "ByteRover image inspect")
    expected_findings = {
        "daemon_network_fatal_reproduced": True,
        "hermes_curate_available_under_network_none": False,
        "hermes_curate_is_provider_dependent": True,
        "hermes_query_available_under_network_none": False,
        "hermes_query_is_provider_dependent": True,
        "native_session_purge_supported": False,
        "offline_search_available_under_network_none": False,
        "session_scoped_directory": False,
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "hermes-byterover-offline-falsification-v1"
        or report.get("status") != BYTEROVER_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_count") != 2
        or report.get("source") != source
        or report.get("findings") != expected_findings
        or report.get("admission")
        != {
            "cluster_confirmation": "not-run",
            "memory_lifecycle_h100": "forbidden-for-this-revision",
            "provider_contract": "native-negative-only",
        }
    ):
        raise EvidenceError("ByteRover result semantics drifted")
    byterover = source.get("byterover")
    hermes = source.get("hermes")
    npm = byterover.get("npm") if isinstance(byterover, dict) else None
    if (
        not isinstance(byterover, dict)
        or byterover.get("repository")
        != "https://github.com/campfirein/byterover-cli"
        or byterover.get("revision") != BYTEROVER_REVISION
        or byterover.get("tree") != "fdaf08c5cf26047d7d458229b90e76d4eb4ff9cf"
        or byterover.get("tag") != "v3.16.1"
        or byterover.get("tag_object") != BYTEROVER_TAG_OBJECT
        or byterover.get("worktree_clean") is not True
        or byterover.get("license_sha256")
        != "99cea22154caece32dde4ee3124d0b6ad44a0f9baab9841889841a567245ab1f"
        or not isinstance(npm, dict)
        or npm.get("sha256")
        != "14039b1ff40820e699484c4db994ee837be66d3919971ce0bc3026287b42dd00"
        or npm.get("integrity")
        != (
            "sha512-uI6zETcy5QO6H29/sdn4BKGWzJl658sjHWxcpO+LHYcmxQj1mAmmi9lluqQZ"
            "YoXXrnrbp+an8NYhjd5MKmDTcw=="
        )
        or not isinstance(hermes, dict)
        or hermes.get("revision") != HERMES_REVISION
        or hermes.get("provider_sha256")
        != "47a6c290fdb735bff3ca4523bced92e45c85ebb3af6af63712b469394a8945a8"
        or source.get("dockerfile_sha256") != BYTEROVER_DOCKERFILE_SHA256
        or source.get("doctor_sha256") != BYTEROVER_DOCTOR_SHA256
    ):
        raise EvidenceError("ByteRover source receipt drifted")
    if _sha256(files["experiment.yaml"]) != BYTEROVER_EXPERIMENT_SHA256:
        raise EvidenceError("ByteRover registered experiment drifted")
    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        image_id != report.get("image", {}).get("image_id")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "node:node"
        or labels.get("org.opencontainers.image.revision") != BYTEROVER_REVISION
        or labels.get("org.cotcodec.byterover-tarball-sha256") != npm["sha256"]
        or labels.get("org.cotcodec.hermes-revision") != HERMES_REVISION
    ):
        raise EvidenceError("ByteRover image receipt drifted")

    projections: list[dict[str, Any]] = []
    execution_identities: list[str] = []
    expected_source_checks = {
        "curate_uses_llm_command": True,
        "no_provider_purge_method": True,
        "profile_directory_ignores_session_id": True,
        "query_uses_llm_command": True,
    }
    for run in (1, 2):
        prefix = f"run-{run}"
        phase_argv: list[Any] = []
        phase_results: list[dict[str, Any]] = []
        for phase, expected_log_count in (("prepare", 3), ("restart", 6)):
            result = _decode_json(files[f"{prefix}/{phase}.json"], f"ByteRover {phase}")
            if (
                result.get("schema_version") != 1
                or result.get("phase") != phase
                or result.get("canary_file_sha256")
                != "ed1d6aec9b7fa8fa94da7c70491e5976bc92e792d985456230d92ad327c3d16a"
                or result.get("source_checks") != expected_source_checks
                or result.get("daemon")
                != {
                    "every_log_has_network_fatal": True,
                    "fatal_network_count": expected_log_count,
                    "log_count": expected_log_count,
                }
            ):
                raise EvidenceError("ByteRover phase identity or daemon evidence drifted")
            version = result.get("version")
            if (
                not isinstance(version, dict)
                or version.get("args") != ["--version"]
                or version.get("exit_code") != 0
                or version.get("timed_out") is not False
                or version.get("stdout")
                != "byterover-cli/3.16.1 linux-arm64 node-v22.21.1"
            ):
                raise EvidenceError("ByteRover version receipt drifted")
            expected_commands = {
                "offline_search": [
                    "search",
                    "Who owns Project Zephyr?",
                    "--format",
                    "json",
                ],
                "hermes_query": ["query", "--", "Who owns Project Zephyr?"],
                "hermes_curate": [
                    "curate",
                    "--",
                    "BYTEROVER_ZEPHYR_7F1D9A Alice owns Project Zephyr",
                ],
            }
            for field, expected_args in expected_commands.items():
                command = result.get(field)
                if (
                    not isinstance(command, dict)
                    or command.get("args") != expected_args
                    or command.get("exit_code") is not None
                    or command.get("signal") != "SIGTERM"
                    or command.get("timed_out") is not True
                    or command.get("stdout") != ""
                    or command.get("stderr") != ""
                ):
                    raise EvidenceError(f"ByteRover {field} falsifier receipt drifted")
            try:
                argv = json.loads(files[f"{prefix}/{phase}.argv.json"])
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise EvidenceError("ByteRover argv is not valid JSON") from exc
            if (
                not isinstance(argv, list)
                or "--network" not in argv
                or argv[argv.index("--network") + 1] != "none"
                or "--read-only" not in argv
                or "--cap-drop" not in argv
                or argv[argv.index("--cap-drop") + 1] != "ALL"
                or "no-new-privileges" not in argv
                or "--user" not in argv
                or argv[argv.index("--user") + 1] != "1000:1000"
                or image_id not in argv
            ):
                raise EvidenceError("ByteRover execution containment drifted")
            phase_argv.append(argv)
            phase_results.append(result)
        projection = _decode_json(
            files[f"{prefix}/stable-projection.json"], "ByteRover projection"
        )
        if (
            projection.get("offline_search_available_under_network_none") is not False
            or projection.get("hermes_query_available_under_network_none") is not False
            or projection.get("hermes_curate_available_under_network_none") is not False
            or projection.get("daemon_network_fatal_reproduced") is not True
            or projection.get("source_checks") != expected_source_checks
            or phase_results[0]["canary_file_sha256"]
            != phase_results[1]["canary_file_sha256"]
        ):
            raise EvidenceError("ByteRover stable projection drifted")
        projections.append(projection)
        execution_identities.append(_sha256(_canonical_json(phase_argv)))
    if projections[0] != projections[1] or len(set(execution_identities)) != 2:
        raise EvidenceError("ByteRover clean repetitions are not distinct and equal")
    if report.get("stable_projection_sha256") != _sha256(_canonical_json(projections[0])):
        raise EvidenceError("ByteRover stable projection receipt drifted")
    return {
        "manifest_root": manifest["root_sha256"],
        "image_id": image_id,
        "stable_projection": projections[0],
        "execution_identities": execution_identities,
    }


def _validate_openviking_run(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute one native OpenViking/Hermes lifecycle run."""

    if set(files) != {"experiment.yaml", "manifest.json", "report.json"}:
        raise EvidenceError("OpenViking run file roster drifted")
    manifest = _decode_json(files["manifest.json"], "OpenViking manifest")
    report = _decode_json(files["report.json"], "OpenViking report")
    if manifest != {
        "schema_version": 1,
        "status": OPENVIKING_STATUS,
        "report": "report.json",
        "report_sha256": _sha256(files["report.json"]),
    }:
        raise EvidenceError("OpenViking manifest or report binding drifted")
    if _sha256(files["experiment.yaml"]) != OPENVIKING_EXPERIMENT_SHA256:
        raise EvidenceError("OpenViking registered experiment drifted")
    if (
        report.get("schema_version") != 1
        or report.get("status") != OPENVIKING_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("provider_quality_evaluated") is not False
        or report.get("h100_admitted") is not False
        or report.get("scope")
        != "native CPU lifecycle and exact Hermes provider transport only"
        or report.get("network")
        != {"external_api_access": False, "internal": True}
    ):
        raise EvidenceError("OpenViking claim boundary drifted")
    runtime = report.get("runtime")
    if (
        not isinstance(runtime, dict)
        or runtime.get("rootfs_read_only") is not True
        or runtime.get("cap_drop") != "ALL"
        or runtime.get("no_new_privileges") is not True
        or runtime.get("gpu_count") != 0
        or not isinstance(runtime.get("host_uid"), int)
        or not isinstance(runtime.get("host_gid"), int)
    ):
        raise EvidenceError("OpenViking runtime containment drifted")
    expected_images = {
        "openviking": "sha256:4b917e25cce8d71a35f6a50f67ff235f0805c179f786c72b71601f26050bca51",
        "model_stub": "sha256:6136cd68a7bed538b224756278fb15344e79e2c19b9640d9b942e41170ade440",
        "hermes_adapter": "sha256:ac1f3e164a6751ee42f225456880231b392ac383b071b71c22c989ea5292274d",
    }
    images = report.get("images")
    if not isinstance(images, dict) or set(images) != set(expected_images):
        raise EvidenceError("OpenViking image roster drifted")
    expected_repositories = {
        "openviking": "cotcodec/openviking",
        "model_stub": "cotcodec/openviking-model-stub",
        "hermes_adapter": "cotcodec/hermes-openviking-adapter",
    }
    for name, expected_id in expected_images.items():
        image = images[name]
        if (
            not isinstance(image, dict)
            or image.get("image_id") != expected_id
            or image.get("repo_digests")
            != [f"{expected_repositories[name]}@{expected_id}"]
            or not isinstance(image.get("inspect_sha256"), str)
            or len(image["inspect_sha256"]) != 64
            or not isinstance(image.get("size"), int)
            or image["size"] <= 0
        ):
            raise EvidenceError(f"OpenViking image receipt drifted: {name}")
    controls = report.get("controls")
    expected_control_hashes = {
        "openviking_config_sha256": (
            "afa7f0e0f089801b4a78c6adc80a229002bfb5a51da1ba05be685cc254eab741"
        ),
        "model_stub_sha256": (
            "6952793d45d1891b7c1739a5d53a8779c126f32032405dab8b7af4ff8a1702ab"
        ),
        "adapter_doctor_sha256": (
            "a3f1c0d34f2b1355d47de5f6b7e103814d2cdca636de50e509eb5e56f90e36c1"
        ),
        "doctor_sha256": OPENVIKING_DOCTOR_SHA256,
        "source_dockerfile_sha256": (
            "4d3bab26fc53b675968e79f96e75c9a639c5f77eada3d327490df69bf6665c64"
        ),
        "stub_dockerfile_sha256": (
            "4a933ff98460c36ed89f718d4cf046ca5ec0da8831ca4b5bcddbf896a79c4366"
        ),
        "adapter_dockerfile_sha256": (
            "d9832dd0e617ba32efc97be96650bc24e42420f4df8d80f0fce1e027ac409f3a"
        ),
    }
    if (
        not isinstance(controls, dict)
        or controls.get("embedding")
        != "deterministic 16-dimensional token-hash stub"
        or controls.get("vlm")
        != "deterministic empty-JSON stub; not used by direct memory tools"
        or any(controls.get(key) != value for key, value in expected_control_hashes.items())
    ):
        raise EvidenceError("OpenViking deterministic control receipts drifted")

    operations = report.get("operations")
    if (
        not isinstance(operations, list)
        or [row.get("name") for row in operations if isinstance(row, dict)]
        != OPENVIKING_OPERATION_SEQUENCE
    ):
        raise EvidenceError("OpenViking operation sequence drifted")
    by_name = {row["name"]: row for row in operations}
    for name, row in by_name.items():
        payload = row.get("payload")
        result = payload.get("result") if isinstance(payload, dict) else None
        if (
            payload.get("status") != "PASS"
            or not isinstance(result, dict)
            or result.get("prompt_active") is not True
            or not isinstance(row.get("stdout_sha256"), str)
            or len(row["stdout_sha256"]) != 64
            or not isinstance(row.get("stderr"), str)
        ):
            raise EvidenceError(f"OpenViking operation receipt drifted: {name}")
    write_a = by_name["tenant-a-write"]["payload"]["result"]
    write_b = by_name["tenant-b-write"]["payload"]["result"]
    canary_a = write_a.get("read", {}).get("content")
    canary_b = write_b.get("read", {}).get("content")
    uri_a = write_a.get("uri")
    uri_b = write_b.get("uri")
    if (
        not isinstance(canary_a, str)
        or not canary_a.startswith("cotcodec-openviking-tenant-a-")
        or not isinstance(canary_b, str)
        or not canary_b.startswith("cotcodec-openviking-tenant-b-")
        or not isinstance(uri_a, str)
        or not uri_a.startswith("viking://user/user-a/")
        or not isinstance(uri_b, str)
        or not uri_b.startswith("viking://user/user-b/")
        or uri_a == uri_b
    ):
        raise EvidenceError("OpenViking tenant write identity drifted")
    if uri_a not in by_name["tenant-a-restart-search"]["payload"]["result"]["uris"]:
        raise EvidenceError("OpenViking restart persistence drifted")
    if (
        uri_a in by_name["tenant-b-cannot-see-a"]["payload"]["result"]["uris"]
        or uri_b in by_name["tenant-a-cannot-see-b"]["payload"]["result"]["uris"]
        or by_name["tenant-a-restart-read"]["payload"]["result"]["read"].get("content")
        != canary_a
    ):
        raise EvidenceError("OpenViking tenant isolation or restart read drifted")
    for tenant, uri in (("a", uri_a), ("b", uri_b)):
        forget = by_name[f"tenant-{tenant}-forget"]["payload"]["result"]
        post = by_name[f"tenant-{tenant}-delete-survives-restart"]["payload"]["result"]
        if (
            forget.get("forgotten", {}).get("status") != "deleted"
            or forget.get("forgotten", {}).get("uri") != uri
            or forget.get("uris") != []
            or post.get("uris") != []
        ):
            raise EvidenceError("OpenViking logical deletion drifted")

    state = report.get("state")
    state_files = state.get("files") if isinstance(state, dict) else None
    if (
        not isinstance(state_files, list)
        or state.get("file_count") != len(state_files)
        or state.get("manifest_sha256") != _sha256(_canonical_json(state_files))
        or not isinstance(state.get("total_bytes"), int)
        or state["total_bytes"] != sum(row.get("bytes", -1) for row in state_files)
    ):
        raise EvidenceError("OpenViking retained-state manifest drifted")
    file_paths = {row.get("path") for row in state_files if isinstance(row, dict)}
    residues = state.get("plaintext_residue")
    proofs = state.get("plaintext_residue_proofs")
    if (
        not isinstance(residues, dict)
        or not isinstance(proofs, dict)
        or set(residues) != {canary_a, canary_b}
        or set(proofs) != {canary_a, canary_b}
    ):
        raise EvidenceError("OpenViking plaintext-residue roster drifted")
    for canary in (canary_a, canary_b):
        if not residues[canary] or len(proofs[canary]) != len(residues[canary]):
            raise EvidenceError("OpenViking plaintext residue was not reproduced")
        for proof in proofs[canary]:
            path = proof.get("path")
            try:
                window = base64.b64decode(proof.get("window_base64"), validate=True)
            except (ValueError, TypeError) as exc:
                raise EvidenceError("OpenViking residue proof is not base64") from exc
            if (
                path not in residues[canary]
                or path not in file_paths
                or not path.startswith("data/vectordb/context/store/")
                or not path.endswith(".ldb")
                or canary.encode() not in window
                or proof.get("window_sha256") != _sha256(window)
                or not isinstance(proof.get("offset"), int)
                or not isinstance(proof.get("window_start"), int)
            ):
                raise EvidenceError("OpenViking plaintext-residue proof drifted")
    logs = report.get("server_logs")
    if (
        not isinstance(logs, list)
        or len(logs) != 3
        or report.get("server_logs_sha256")
        != [_sha256(log.encode("utf-8")) for log in logs]
    ):
        raise EvidenceError("OpenViking server-log receipts drifted")
    return {
        "image_ids": expected_images,
        "operation_count": len(operations),
        "state_manifest_sha256": state["manifest_sha256"],
        "residue_file_count": sum(len(paths) for paths in residues.values()),
        "report_sha256": _sha256(files["report.json"]),
    }


def validate_openviking_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute two independent OpenViking/Hermes lifecycle negatives."""

    if set(files) != OPENVIKING_REQUIRED_FILES:
        raise EvidenceError("OpenViking evidence file roster drifted")
    verified: list[dict[str, Any]] = []
    for run in (1, 2):
        verified.append(
            _validate_openviking_run(
                {
                    "experiment.yaml": files["experiment.yaml"],
                    "manifest.json": files[f"run-{run}/manifest.json"],
                    "report.json": files[f"run-{run}/report.json"],
                }
            )
        )
    if (
        verified[0]["image_ids"] != verified[1]["image_ids"]
        or verified[0]["operation_count"] != verified[1]["operation_count"]
        or verified[0]["residue_file_count"] <= 0
        or verified[1]["residue_file_count"] <= 0
        or verified[0]["report_sha256"] == verified[1]["report_sha256"]
    ):
        raise EvidenceError("OpenViking independent repetitions drifted")
    return {
        "image_ids": verified[0]["image_ids"],
        "operation_count": verified[0]["operation_count"],
        "state_manifest_sha256s": [row["state_manifest_sha256"] for row in verified],
        "residue_file_counts": [row["residue_file_count"] for row in verified],
        "execution_identity_sha256s": [row["report_sha256"] for row in verified],
    }


def _validate_hindsight_run(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute one native Hindsight/Hermes lifecycle run."""

    if set(files) != {"experiment.yaml", "manifest.json", "report.json"}:
        raise EvidenceError("Hindsight run file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Hindsight manifest")
    report = _decode_json(files["report.json"], "Hindsight report")
    if manifest != {
        "schema_version": 1,
        "status": HINDSIGHT_STATUS,
        "report": "report.json",
        "report_sha256": _sha256(files["report.json"]),
    }:
        raise EvidenceError("Hindsight manifest or report binding drifted")
    if _sha256(files["experiment.yaml"]) != HINDSIGHT_EXPERIMENT_SHA256:
        raise EvidenceError("Hindsight registered experiment drifted")
    if (
        report.get("schema_version") != 1
        or report.get("status") != HINDSIGHT_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("provider_quality_evaluated") is not False
        or report.get("h100_admitted") is not False
        or report.get("scope")
        != "native CPU lifecycle and exact Hermes Hindsight provider transport only"
        or report.get("network")
        != {"external_api_access": False, "internal": True}
    ):
        raise EvidenceError("Hindsight claim boundary drifted")

    runtime = report.get("runtime")
    if runtime != {
        "cap_drop": "ALL",
        "database_data_checksums": True,
        "database_mode": "external-postgresql-pgvector",
        "gpu_count": 0,
        "no_new_privileges": True,
        "rootfs_read_only": True,
        "stable_worker_id": "cotcodec-hermes-hindsight-doctor",
    }:
        raise EvidenceError("Hindsight runtime containment drifted")

    expected_images = {
        "hermes_adapter": (
            "sha256:0ae493490c0539a08343eec995865fdb0651562896f58cfd8fc0ae720b6d9c06"
        ),
        "hindsight_backend": (
            "sha256:91ddf1da2ac339c4b44f2a837c1536965a3cf41f2fe7b332416b65e29b4b424e"
        ),
        "model_stub": (
            "sha256:6136cd68a7bed538b224756278fb15344e79e2c19b9640d9b942e41170ade440"
        ),
        "postgres_pgvector": (
            "sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff"
        ),
    }
    expected_repositories = {
        "hermes_adapter": "cotcodec/hermes-hindsight-adapter",
        "hindsight_backend": "cotcodec/hermes-hindsight-backend",
        "model_stub": "cotcodec/openviking-model-stub",
        "postgres_pgvector": "pgvector/pgvector",
    }
    images = report.get("images")
    if not isinstance(images, dict) or set(images) != set(expected_images):
        raise EvidenceError("Hindsight image roster drifted")
    for name, expected_id in expected_images.items():
        image = images[name]
        if (
            not isinstance(image, dict)
            or image.get("image_id") != expected_id
            or image.get("repo_digests")
            != [f"{expected_repositories[name]}@{expected_id}"]
            or not isinstance(image.get("inspect_sha256"), str)
            or len(image["inspect_sha256"]) != 64
            or not isinstance(image.get("size"), int)
            or image["size"] <= 0
        ):
            raise EvidenceError(f"Hindsight image receipt drifted: {name}")

    controls = report.get("controls")
    expected_control_hashes = {
        "adapter_dockerfile_sha256": (
            "b771259bb8d8b18c1722ce1ea352cd5c8565908b9dbd3801411257d2efc4ba02"
        ),
        "adapter_doctor_sha256": (
            "37ca1e3282fee036a78f502be022fe1d401b8302ad2f84856137af033118b093"
        ),
        "backend_dockerfile_sha256": (
            "f367f49d3b75e84b7ab0e4f25ebcaf773f4ff0221e3c0d133e2acca7b6ee1290"
        ),
        "doctor_sha256": HINDSIGHT_DOCTOR_SHA256,
        "model_stub_sha256": (
            "6952793d45d1891b7c1739a5d53a8779c126f32032405dab8b7af4ff8a1702ab"
        ),
    }
    if (
        not isinstance(controls, dict)
        or controls.get("embedding")
        != "deterministic 16-dimensional token-hash stub"
        or controls.get("model_calls") != 0
        or controls.get("external_network_calls") != 0
        or controls.get("postgres_repo_digest")
        != (
            "pgvector/pgvector@sha256:"
            "78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff"
        )
        or any(
            controls.get(key) != value for key, value in expected_control_hashes.items()
        )
    ):
        raise EvidenceError("Hindsight deterministic control receipts drifted")

    provider = report.get("provider_contract")
    if provider != {
        "delete_path": "hindsight-client-admin-delete-bank",
        "exact_hermes_provider": True,
        "hermes_client_version": "0.6.1",
        "hermes_purge_tool_exposed": False,
        "native_service_version": "0.9.0",
        "tool_names": [
            "hindsight_retain",
            "hindsight_recall",
            "hindsight_reflect",
        ],
    }:
        raise EvidenceError("Hindsight provider contract drifted")

    operations = report.get("operations")
    if (
        not isinstance(operations, list)
        or [row.get("name") for row in operations if isinstance(row, dict)]
        != HINDSIGHT_OPERATION_SEQUENCE
    ):
        raise EvidenceError("Hindsight operation sequence drifted")
    by_name = {row["name"]: row for row in operations}
    expected_tools = [
        "hindsight_retain",
        "hindsight_recall",
        "hindsight_reflect",
    ]
    for name, row in by_name.items():
        payload = row.get("payload")
        result = payload.get("result") if isinstance(payload, dict) else None
        if (
            payload.get("status") != "PASS"
            or not isinstance(result, dict)
            or result.get("prompt_active") is not True
            or result.get("purge_tool_exposed") is not False
            or result.get("tool_names") != expected_tools
            or not isinstance(row.get("stdout_sha256"), str)
            or len(row["stdout_sha256"]) != 64
            or not isinstance(row.get("stderr"), str)
        ):
            raise EvidenceError(f"Hindsight operation receipt drifted: {name}")

    state = report.get("state")
    state_files = state.get("files") if isinstance(state, dict) else None
    if (
        not isinstance(state_files, list)
        or state.get("file_count") != len(state_files)
        or state.get("manifest_sha256") != _sha256(_canonical_json(state_files))
        or not isinstance(state.get("total_bytes"), int)
        or state["total_bytes"] != sum(row.get("bytes", -1) for row in state_files)
    ):
        raise EvidenceError("Hindsight retained-state manifest drifted")
    file_paths = {row.get("path") for row in state_files if isinstance(row, dict)}
    residues = state.get("plaintext_residue")
    proofs = state.get("plaintext_residue_proofs")
    if (
        not isinstance(residues, dict)
        or not isinstance(proofs, dict)
        or set(residues) != set(proofs)
        or len(residues) != 2
    ):
        raise EvidenceError("Hindsight plaintext-residue roster drifted")
    canary_a = next(
        (value for value in residues if value.startswith("cotcodec-hindsight-tenant-a-")),
        None,
    )
    canary_b = next(
        (value for value in residues if value.startswith("cotcodec-hindsight-tenant-b-")),
        None,
    )
    if not isinstance(canary_a, str) or not isinstance(canary_b, str):
        raise EvidenceError("Hindsight canary identities drifted")
    for canary in (canary_a, canary_b):
        paths = residues[canary]
        canary_proofs = proofs[canary]
        if (
            len(paths) != 5
            or len(canary_proofs) != 5
            or sum(path.startswith("pgdata/base/") for path in paths) != 4
            or sum(path.startswith("pgdata/pg_wal/") for path in paths) != 1
        ):
            raise EvidenceError("Hindsight residue shape drifted")
        for proof in canary_proofs:
            path = proof.get("path")
            try:
                window = base64.b64decode(proof.get("window_base64"), validate=True)
            except (ValueError, TypeError) as exc:
                raise EvidenceError("Hindsight residue proof is not base64") from exc
            if (
                path not in paths
                or path not in file_paths
                or canary.encode() not in window
                or proof.get("window_sha256") != _sha256(window)
                or not isinstance(proof.get("offset"), int)
                or not isinstance(proof.get("window_start"), int)
            ):
                raise EvidenceError("Hindsight plaintext-residue proof drifted")

    own_receipts = {
        "tenant-a-tool-retain": canary_a,
        "tenant-a-prefetch": canary_a,
        "tenant-b-search-own": canary_b,
        "tenant-a-full-restart-search": canary_a,
        "tenant-b-full-restart-search": canary_b,
    }
    for name, canary in own_receipts.items():
        if canary not in json.dumps(by_name[name]["payload"]["result"], sort_keys=True):
            raise EvidenceError(f"Hindsight own-memory result drifted: {name}")
    if (
        canary_a
        in json.dumps(by_name["tenant-b-cannot-see-a"]["payload"]["result"])
        or canary_b
        in json.dumps(by_name["tenant-a-cannot-see-b"]["payload"]["result"])
    ):
        raise EvidenceError("Hindsight tenant-isolation result drifted")
    for name in (
        "tenant-a-admin-delete",
        "tenant-b-admin-delete",
        "tenant-a-delete-survives-full-restart",
        "tenant-b-delete-survives-full-restart",
    ):
        result = by_name[name]["payload"]["result"]
        if result.get("recalled") != {"result": "No relevant memories found."}:
            raise EvidenceError(f"Hindsight logical-delete result drifted: {name}")

    for field in ("backend_logs", "postgres_logs"):
        logs = report.get(field)
        if (
            not isinstance(logs, list)
            or len(logs) != 3
            or report.get(f"{field}_sha256")
            != [_sha256(log.encode("utf-8")) for log in logs]
        ):
            raise EvidenceError(f"Hindsight {field} receipts drifted")
    return {
        "canaries": [canary_a, canary_b],
        "image_ids": expected_images,
        "operation_count": len(operations),
        "state_manifest_sha256": state["manifest_sha256"],
        "residue_file_count": sum(len(paths) for paths in residues.values()),
        "report_sha256": _sha256(files["report.json"]),
    }


def validate_hindsight_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute two independent Hindsight/Hermes lifecycle negatives."""

    if set(files) != HINDSIGHT_REQUIRED_FILES:
        raise EvidenceError("Hindsight evidence file roster drifted")
    verified = [
        _validate_hindsight_run(
            {
                "experiment.yaml": files["experiment.yaml"],
                "manifest.json": files[f"run-{run}/manifest.json"],
                "report.json": files[f"run-{run}/report.json"],
            }
        )
        for run in (1, 2)
    ]
    if (
        verified[0]["image_ids"] != verified[1]["image_ids"]
        or verified[0]["operation_count"] != verified[1]["operation_count"]
        or verified[0]["residue_file_count"] != 10
        or verified[1]["residue_file_count"] != 10
        or verified[0]["report_sha256"] == verified[1]["report_sha256"]
        or set(verified[0]["canaries"]) & set(verified[1]["canaries"])
    ):
        raise EvidenceError("Hindsight independent repetitions drifted")
    return {
        "image_ids": verified[0]["image_ids"],
        "operation_count": verified[0]["operation_count"],
        "state_manifest_sha256s": [row["state_manifest_sha256"] for row in verified],
        "residue_file_counts": [row["residue_file_count"] for row in verified],
        "execution_identity_sha256s": [row["report_sha256"] for row in verified],
    }


def validate_hermes_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the exact Hermes conformance roster, results, and receipts."""

    expected_files = {"manifest.json", "report.json", "registered-experiment.yaml"} | {
        f"logs/{name}" for name in HERMES_LOG_ROSTER
    }
    if set(files) != expected_files:
        raise EvidenceError("Hermes evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Hermes manifest")
    report = _decode_json(files["report.json"], "Hermes report")
    if manifest.get("schema_version") != 1 or manifest.get("status") != "FAIL":
        raise EvidenceError("Hermes manifest identity drifted")
    if manifest.get("study") != "hermes-memory-provider-conformance-v1":
        raise EvidenceError("Hermes study identity drifted")
    log_receipts = manifest.get("log_sha256s")
    if not isinstance(log_receipts, dict) or set(log_receipts) != HERMES_LOG_ROSTER:
        raise EvidenceError("Hermes log roster drifted")
    for name, expected in log_receipts.items():
        if expected != _sha256(files[f"logs/{name}"]):
            raise EvidenceError(f"Hermes log SHA-256 drifted: {name}")
    experiment_sha256 = _sha256(files["registered-experiment.yaml"])
    if (
        manifest.get("experiment_sha256") != experiment_sha256
        or report.get("experiment_sha256") != experiment_sha256
        or manifest.get("report_sha256") != _sha256(files["report.json"])
    ):
        raise EvidenceError("Hermes experiment or report binding drifted")
    if (
        report.get("status") != "FAIL"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("provider_roster") != PROVIDER_ROSTER
    ):
        raise EvidenceError("Hermes report identity drifted")
    results = report.get("results")
    if not isinstance(results, list):
        raise EvidenceError("Hermes result rows are missing")
    by_group: dict[str, dict[str, Any]] = {}
    for row in results:
        if not isinstance(row, dict) or not isinstance(row.get("group"), str):
            raise EvidenceError("Hermes result row is invalid")
        group = row["group"]
        if group in by_group:
            raise EvidenceError("Hermes result group is duplicated")
        by_group[group] = row
    if set(by_group) != set(HERMES_RESULT_STATUS):
        raise EvidenceError("Hermes result group roster drifted")
    if {group: row.get("status") for group, row in by_group.items()} != HERMES_RESULT_STATUS:
        raise EvidenceError("Hermes result status map drifted")
    source = report.get("source_contract")
    if not isinstance(source, dict):
        raise EvidenceError("Hermes source contract is missing")
    if source.get("hermes", {}).get("revision") != HERMES_REVISION:
        raise EvidenceError("Hermes source revision drifted")
    if source.get("memori", {}).get("revision") != MEMORI_REVISION:
        raise EvidenceError("Memori source revision drifted")
    measurement = by_group["hindsight-strict-timeout-probe"].get("measurement")
    if (
        not isinstance(measurement, dict)
        or measurement.get("budget_seconds") != 0.05
        or not isinstance(measurement.get("elapsed_seconds"), (int, float))
        or measurement["elapsed_seconds"] <= measurement["budget_seconds"]
    ):
        raise EvidenceError("Hermes Hindsight timeout negative drifted")
    honcho = by_group["honcho"].get("summary")
    if not isinstance(honcho, dict) or honcho.get("failed") != 1:
        raise EvidenceError("Hermes Honcho negative drifted")
    return {
        "experiment_sha256": experiment_sha256,
        "failed_groups": ["honcho", "hindsight-strict-timeout-probe"],
        "result_status": HERMES_RESULT_STATUS,
    }


def validate_mem0_lifecycle_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the bounded Mem0 lifecycle-adapter negative."""

    if set(files) != MEM0_LIFECYCLE_REQUIRED_FILES:
        raise EvidenceError("Mem0 lifecycle evidence file roster drifted")
    experiment_sha = _sha256(files["experiment.yaml"])
    if experiment_sha != MEM0_LIFECYCLE_EXPERIMENT_SHA256:
        raise EvidenceError("Mem0 lifecycle registered experiment drifted")

    source = _decode_json(files["source-context.json"], "Mem0 source context")
    source_without_receipt = dict(source)
    source_receipt_sha = source_without_receipt.pop("receipt_sha256", None)
    if (
        source.get("system_id") != "mem0"
        or source.get("revision") != MEM0_LIFECYCLE_REVISION
        or source.get("source_archive_sha256")
        != MEM0_LIFECYCLE_SOURCE_ARCHIVE_SHA256
        or source.get("excluded_unsafe_archive_paths") != []
        or source_receipt_sha
        != _sha256(
            json.dumps(
                source_without_receipt,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        )
    ):
        raise EvidenceError("Mem0 source-context receipt drifted")

    try:
        inspect_value = json.loads(files["image-inspect.json"])
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvidenceError("Mem0 image inspect is invalid JSON") from exc
    if not isinstance(inspect_value, list) or len(inspect_value) != 1:
        raise EvidenceError("Mem0 image inspect must contain exactly one image")
    inspect = inspect_value[0]
    if not isinstance(inspect, dict):
        raise EvidenceError("Mem0 image inspect entry is invalid")
    image_id = inspect.get("Id")
    labels = inspect.get("Config", {}).get("Labels", {})
    expected_label_hashes = {
        "org.cotcodec.mem0-lifecycle-sidecar-sha256": _sha256(
            files["infra/memory-baselines/mem0_lifecycle_sidecar.py"]
        ),
        "org.cotcodec.mem0-lifecycle-doctor-sha256": _sha256(
            files["scripts/run_mem0_lifecycle_doctor.py"]
        ),
        "org.cotcodec.mem0-lifecycle-experiment-sha256": experiment_sha,
    }
    if (
        not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision")
        != MEM0_LIFECYCLE_REVISION
        or labels.get("org.cotcodec.source-archive-sha256")
        != MEM0_LIFECYCLE_SOURCE_ARCHIVE_SHA256
        or labels.get("org.cotcodec.memory-lifecycle-adapter")
        != "mem0-native-lifecycle-v1"
        or labels.get("org.cotcodec.scientific-result") != "false"
        or labels.get("org.opencontainers.image.cotcodec-source-state")
        != "dirty-development"
        or any(labels.get(key) != value for key, value in expected_label_hashes.items())
    ):
        raise EvidenceError("Mem0 lifecycle image receipt drifted")

    expected_code_receipt = {
        name: {"bytes": len(files[name]), "sha256": _sha256(files[name])}
        for name in sorted(MEM0_LIFECYCLE_CODE_FILES)
    }
    expected_gates = {
        "all_resident_records_are_archive",
        "branch_mutation_does_not_change_sibling",
        "checkpoint_verifies_persisted_state",
        "crash_scope_plaintext_proofs_capture_all_hits",
        "delete_removes_record",
        "divergent_retry_rejected",
        "equal_prefix_branch_roots_match",
        "idempotent_retry_receipt_exact",
        "interrupted_operation_fail_closed",
        "maintain_and_feedback_capabilities_absent",
        "post_native_crash_observed",
        "purge_removes_logical_state",
        "purged_scopes_remove_plaintext_canaries",
        "restart_evidence_identity_exact_and_score_delta_le_1e-6",
        "source_and_adapter_receipts_exact",
        "update_preserves_transitive_lineage",
        "updated_value_retrievable",
    }
    expected_crash_scope_hits = [
        "scope-8e3263ffbef46b4835414a69388b33c3c9946d071313ddfd1b437dcb5496058b/history.db",
        "scope-8e3263ffbef46b4835414a69388b33c3c9946d071313ddfd1b437dcb5496058b/"
        "qdrant/collection/cotcodec_memory/storage.sqlite",
    ]
    projections: list[dict[str, Any]] = []
    proof_roots: list[str] = []
    report_hashes: list[str] = []
    for run in (1, 2):
        prefix = f"run-{run}"
        report = _decode_json(files[f"{prefix}/report.json"], f"Mem0 {prefix} report")
        manifest = _decode_json(
            files[f"{prefix}/manifest.json"], f"Mem0 {prefix} manifest"
        )
        stdout = _decode_json(files[f"{prefix}/stdout.txt"], f"Mem0 {prefix} stdout")
        if stdout != report or files[f"{prefix}/stderr.txt"] != b"":
            raise EvidenceError(f"Mem0 {prefix} output transport drifted")
        report_receipt = {
            "bytes": len(files[f"{prefix}/report.json"]),
            "sha256": _sha256(files[f"{prefix}/report.json"]),
        }
        if (
            manifest.get("schema_version") != 1
            or manifest.get("status") != MEM0_LIFECYCLE_STATUS
            or manifest.get("scientific_result") is not False
            or manifest.get("publication_ready") is not False
            or manifest.get("experiment_sha256") != experiment_sha
            or manifest.get("artifacts") != {"report.json": report_receipt}
            or manifest.get("artifact_root_sha256")
            != _sha256(
                json.dumps(
                    {"report.json": report_receipt},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            )
        ):
            raise EvidenceError(f"Mem0 {prefix} manifest drifted")
        projection = report.get("stable_projection")
        gates = projection.get("gates") if isinstance(projection, dict) else None
        costs = report.get("costs")
        proofs = report.get("crash_scope_plaintext_proofs")
        if not isinstance(proofs, dict) or set(proofs) != set(expected_crash_scope_hits):
            raise EvidenceError(f"Mem0 {prefix} crash plaintext proof roster drifted")
        crash_needle = b"crash-window-canary-883"
        expected_needle_sha = _sha256(crash_needle)
        for path, entries in proofs.items():
            if not isinstance(entries, list) or len(entries) != 1:
                raise EvidenceError(f"Mem0 {prefix} crash plaintext proof shape drifted")
            proof = entries[0]
            expected_keys = {
                "file_bytes",
                "file_sha256",
                "needle_sha256",
                "offset",
                "window_base64",
                "window_sha256",
                "window_start",
            }
            if not isinstance(proof, dict) or set(proof) != expected_keys:
                raise EvidenceError(f"Mem0 {prefix} crash plaintext proof shape drifted")
            try:
                window = base64.b64decode(proof["window_base64"], validate=True)
            except (TypeError, ValueError) as exc:
                raise EvidenceError(
                    f"Mem0 {prefix} crash plaintext proof is not base64"
                ) from exc
            offset = proof.get("offset")
            window_start = proof.get("window_start")
            file_bytes = proof.get("file_bytes")
            relative_offset = (
                offset - window_start
                if isinstance(offset, int) and isinstance(window_start, int)
                else -1
            )
            file_sha = proof.get("file_sha256")
            if (
                not isinstance(file_bytes, int)
                or file_bytes < len(window)
                or not isinstance(file_sha, str)
                or len(file_sha) != 64
                or any(character not in "0123456789abcdef" for character in file_sha)
                or proof.get("needle_sha256") != expected_needle_sha
                or proof.get("window_sha256") != _sha256(window)
                or not isinstance(offset, int)
                or not isinstance(window_start, int)
                or offset < 0
                or window_start < 0
                or relative_offset < 0
                or window[relative_offset : relative_offset + len(crash_needle)]
                != crash_needle
            ):
                raise EvidenceError(f"Mem0 {prefix} crash plaintext proof drifted: {path}")
        proof_roots.append(
            _sha256(
                json.dumps(
                    proofs,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            )
        )
        if (
            report.get("schema_version") != 1
            or report.get("study") != "mem0-native-lifecycle-doctor-v1"
            or report.get("status") != MEM0_LIFECYCLE_STATUS
            or report.get("scientific_result") is not False
            or report.get("publication_ready") is not False
            or report.get("h100_admission") != "blocked"
            or report.get("experiment_sha256") != experiment_sha
            or report.get("source_receipt") != source
            or report.get("code_receipt") != expected_code_receipt
            or report.get("purged_scope_plaintext_hits") != []
            or report.get("crash_scope_plaintext_hits") != expected_crash_scope_hits
            or not isinstance(projection, dict)
            or not isinstance(gates, dict)
            or set(gates) != expected_gates
            or not all(gates.values())
            or not isinstance(projection.get("crash_recovery"), dict)
            or projection["crash_recovery"].get("continuation_recovered") is not False
            or projection["crash_recovery"].get("fail_closed") is not True
            or projection["crash_recovery"].get("plaintext_residue_cleared")
            != (not report["crash_scope_plaintext_hits"])
            or projection["crash_recovery"].get("plaintext_residue_file_count")
            != len(report["crash_scope_plaintext_hits"])
            or report.get("stable_projection_sha256")
            != _sha256(
                json.dumps(
                    projection,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            )
            or not isinstance(costs, list)
            or not costs
        ):
            raise EvidenceError(f"Mem0 {prefix} result semantics drifted")
        if any(
            not isinstance(cost, dict)
            or not isinstance(cost.get("latency_ms"), (int, float))
            or not math.isfinite(cost["latency_ms"])
            or cost["latency_ms"] < 0
            for cost in costs
        ):
            raise EvidenceError(f"Mem0 {prefix} cost ledger drifted")
        runtime = report.get("runtime")
        if (
            not isinstance(runtime, dict)
            or runtime.get("container_image_id") != image_id
            or runtime.get("containerized") is not True
            or runtime.get("network_mode") != "none"
            or runtime.get("platform_machine") != "aarch64"
            or runtime.get("platform_system") != "Linux"
            or runtime.get("sudo_used") is not False
            or runtime.get("scheduler_job_id") is not None
        ):
            raise EvidenceError(f"Mem0 {prefix} containment receipt drifted")
        projections.append(projection)
        report_hashes.append(report_receipt["sha256"])
    if (
        projections[0] != projections[1]
        or len(set(report_hashes)) != 2
        or len(set(proof_roots)) != 2
    ):
        raise EvidenceError("Mem0 repetitions are not distinct with equal projections")
    return {
        "image_id": image_id,
        "stable_projection": projections[0],
        "stable_projection_sha256": _sha256(
            json.dumps(
                projections[0],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ),
        "report_sha256s": report_hashes,
        "crash_scope_plaintext_proof_roots": proof_roots,
        "source_receipt_sha256": source_receipt_sha,
    }


def validate_neo4j_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Recompute the native Neo4j preference lifecycle conformance contract."""

    if set(files) != NEO4J_REQUIRED_FILES:
        raise EvidenceError("Neo4j evidence file roster drifted")
    manifest = _decode_json(files["manifest.json"], "Neo4j manifest")
    report = _decode_json(files["report.json"], "Neo4j report")
    if manifest.get("schema_version") != 1 or manifest.get("status") != NEO4J_STATUS:
        raise EvidenceError("Neo4j manifest identity drifted")
    manifest_without_root = dict(manifest)
    manifest_root = manifest_without_root.pop("manifest_sha256", None)
    if manifest_root != _sha256(_canonical_json(manifest_without_root)):
        raise EvidenceError("Neo4j manifest self-root drifted")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
        "experiment.yaml",
        "report.json",
    }:
        raise EvidenceError("Neo4j manifest artifact roster drifted")
    for name in ("experiment.yaml", "report.json"):
        if artifacts[name] != {
            "bytes": len(files[name]),
            "sha256": _sha256(files[name]),
        }:
            raise EvidenceError(f"Neo4j artifact receipt drifted: {name}")

    source = report.get("source")
    runtime = report.get("runtime")
    projection = report.get("semantic_projection")
    expected_projection = {
        "active_count": 1,
        "history_count": 2,
        "model_calls": 0,
        "node_semantics": [
            [
                "cotcodec-neo4j-a",
                "consultants",
                "Prefer junior consultants",
                True,
            ],
            [
                "cotcodec-neo4j-a",
                "consultants",
                "Prefer senior consultants",
                False,
            ],
            [
                "cotcodec-neo4j-b",
                "format",
                "Prefer concise output",
                False,
            ],
        ],
        "past_count": 1,
        "purge_edges": 0,
        "purge_nodes": 0,
        "restart_hash_preserved": True,
        "supersession_edge_count": 1,
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "neo4j-preference-supersession-lifecycle-v1"
        or report.get("status") != NEO4J_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("gpu_hours") != 0
        or report.get("runtime_lane") != "local-arm64"
        or report.get("confirmation_required") is not True
        or projection != expected_projection
        or not isinstance(source, dict)
        or source.get("revision") != NEO4J_REVISION
        or not isinstance(runtime, dict)
        or runtime.get("platform") != "linux/arm64"
        or runtime.get("network") != "private-internal-only"
        or runtime.get("sudo_used") is not False
        or runtime.get("neo4j_image_id")
        != "sha256:1184ab86519418c5a08f6abc06290afddea24a9ef86591379c33d082224cb8de"
    ):
        raise EvidenceError("Neo4j report identity or semantic projection drifted")
    client_image = runtime.get("client_image_id")
    if not isinstance(client_image, str) or not client_image.startswith("sha256:"):
        raise EvidenceError("Neo4j client image identity is invalid")

    repeats = report.get("repeats")
    if not isinstance(repeats, list) or [row.get("repeat") for row in repeats] != [1, 2]:
        raise EvidenceError("Neo4j clean-volume repeat roster drifted")
    execution_roots: list[str] = []
    for repeat in repeats:
        if not isinstance(repeat, dict) or repeat.get("semantic_projection") != projection:
            raise EvidenceError("Neo4j repeat semantic projection drifted")
        establish = repeat.get("establish")
        verified = repeat.get("verify_purge")
        empty = repeat.get("verify_empty")
        if not all(isinstance(item, dict) for item in (establish, verified, empty)):
            raise EvidenceError("Neo4j repeat phase receipt is missing")
        state = establish.get("state")
        expected = establish.get("expected")
        if not isinstance(state, dict) or not isinstance(expected, dict):
            raise EvidenceError("Neo4j establish state is missing")
        nodes = state.get("nodes")
        edges = state.get("supersession_edges")
        if not isinstance(nodes, list) or len(nodes) != 3 or not isinstance(edges, list):
            raise EvidenceError("Neo4j native state roster drifted")
        metadata = []
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("metadata"), str):
                raise EvidenceError("Neo4j node lineage is invalid")
            metadata.append(json.loads(node["metadata"]))
        if sorted(item.get("event_id") for item in metadata) != [
            "event-001",
            "event-002",
            "event-003",
        ]:
            raise EvidenceError("Neo4j event lineage drifted")
        old = next(node for node in nodes if node["preference"] == "Prefer junior consultants")
        if old.get("superseded") is not True or not isinstance(old.get("valid_until"), str):
            raise EvidenceError("Neo4j superseded preference validity drifted")
        if (
            establish.get("source_revision") != NEO4J_REVISION
            or establish.get("model_calls") != 0
            or len(edges) != 1
            or verified.get("state_sha256") != state.get("state_sha256")
            or verified.get("model_calls") != 0
            or empty.get("nodes") != 0
            or empty.get("edges") != 0
            or empty.get("model_calls") != 0
        ):
            raise EvidenceError("Neo4j restart, purge, or model-call gate drifted")
        execution_root = state.get("state_sha256")
        if not isinstance(execution_root, str) or len(execution_root) != 64:
            raise EvidenceError("Neo4j execution state root is invalid")
        execution_roots.append(execution_root)
    if len(set(execution_roots)) != 2:
        raise EvidenceError("Neo4j clean-volume repetitions lack distinct state roots")
    return {
        "manifest_root": manifest_root,
        "semantic_projection": projection,
        "execution_state_roots": execution_roots,
        "client_image_id": client_image,
    }


def _total_projection(report: dict[str, Any]) -> dict[str, Any]:
    native = report.get("native_report")
    if not isinstance(native, dict):
        raise EvidenceError("Total Recall report lacks native_report")
    return {
        "status": native.get("status"),
        "source_revision": native.get("source_revision"),
        "automatic_transition": native.get("automatic_transition"),
        "vector_preserving_control": native.get("vector_preserving_control"),
        "gates": native.get("gates"),
        "expected_negative_finding": native.get("expected_negative_finding"),
    }


def seal_total_recall(primary: Path, replication: Path) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []
    input_receipts: list[dict[str, Any]] = []
    image_ids: list[str] = []
    execution_identities: list[str] = []
    for role, root in (("primary", primary), ("replication", replication)):
        manifest, files = _verify_manifest(root)
        decoded = {
            name: base64.b64decode(receipt["content_base64"])
            for name, receipt in files.items()
        }
        verified = validate_total_recall_files(decoded)
        projections.append(verified["projection"])
        input_receipts.append(verified["input_receipt"])
        image_ids.append(verified["image_id"])
        execution_identities.append(verified["execution_identity_sha256"])
        runs.append(
            {
                "role": role,
                "manifest_file_sha256": files["manifest.json"]["sha256"],
                "manifest_root_sha256": manifest["manifest_sha256"],
                "execution_identity_sha256": verified["execution_identity_sha256"],
                "files": files,
            }
        )
    if primary.resolve() == replication.resolve():
        raise EvidenceError("Total Recall primary and replication roots must differ")
    if projections[0] != projections[1]:
        raise EvidenceError("Total Recall deterministic result projections differ")
    if input_receipts[0] != input_receipts[1] or image_ids[0] != image_ids[1]:
        raise EvidenceError("Total Recall input or image identity differs across runs")
    if len(set(execution_identities)) != 2:
        raise EvidenceError("Total Recall runs lack distinct execution identities")
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "total-recall-oss",
        "evidence_grade": "local-negative-reproduced",
        "status": TOTAL_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/strvmarv/total-recall": TOTAL_REVISION,
        },
        "run_count": 2,
        "shared_image_id": image_ids[0],
        "shared_input_receipt_sha256": _sha256(
            json.dumps(input_receipts[0], sort_keys=True, separators=(",", ":")).encode()
        ),
        "deterministic_projection": projections[0],
        "runs": runs,
    }


def seal_allmem(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(
        experiment.read_bytes()
    ):
        raise EvidenceError("All-Mem result does not bind the registered experiment")
    decoded = _decode_captured_files(files)
    verified = validate_allmem_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "all-mem",
        "evidence_grade": "local-negative-reproduced",
        "status": ALLMEM_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/LvCan926/All-Mem": ALLMEM_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "stable_semantic_projection_sha256": verified[
            "stable_semantic_projection_sha256"
        ],
        "execution_identity_sha256s": verified["execution_identity_sha256s"],
        "observed_rank_orders": verified["observed_rank_orders"],
        "claim_boundary": {
            "split_merge_raw_recovery_failed": True,
            "update_version_recovery_passed": True,
            "h100_admission": "forbidden-for-this-revision",
            "memory_quality_measured": False,
        },
        "files": files,
    }


def seal_hermes(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    experiment_bytes = experiment.read_bytes()
    files["registered-experiment.yaml"] = {
        "bytes": len(experiment_bytes),
        "sha256": _sha256(experiment_bytes),
        "content_base64": base64.b64encode(experiment_bytes).decode("ascii"),
    }
    verified = validate_hermes_files(
        {
            name: base64.b64decode(receipt["content_base64"])
            for name, receipt in files.items()
        }
    )
    return {
        "schema_version": 1,
        "evidence_kind": "provider-conformance-reproduction",
        "source_id": "hermes-provider-conformance",
        "evidence_grade": "local-conformance-reproduced",
        "status": "FAIL",
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/NousResearch/hermes-agent": HERMES_REVISION,
            "https://github.com/MemoriLabs/Memori": MEMORI_REVISION,
        },
        "provider_roster": PROVIDER_ROSTER,
        "failed_groups": verified["failed_groups"],
        "result_status": verified["result_status"],
        "canonical_generation": "v2",
        "supersedes": "v1-memori-executable-absent",
        "files": files,
    }


def seal_neo4j(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(
        experiment.read_bytes()
    ):
        raise EvidenceError("Neo4j result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_neo4j_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-lifecycle-conformance-reproduction",
        "source_id": "neo4j-agent-memory",
        "evidence_grade": "local-conformance-reproduced",
        "status": NEO4J_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/neo4j-labs/agent-memory": NEO4J_REVISION,
        },
        "runtime_lane": "local-arm64",
        "confirmation_required": True,
        "run_count": 2,
        "semantic_projection": verified["semantic_projection"],
        "execution_state_roots": verified["execution_state_roots"],
        "client_image_id": verified["client_image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "files": files,
    }


def seal_hippo(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(experiment.read_bytes()):
        raise EvidenceError("Hippo result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_hippo_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "hippo-memory",
        "evidence_grade": "local-negative-reproduced",
        "status": HIPPO_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/kitfunso/hippo-memory": HIPPO_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "stable_projection": verified["stable_projection"],
        "execution_identity_sha256s": verified["execution_identities"],
        "files": files,
    }


def seal_supermemory(root: Path, experiment: Path) -> dict[str, Any]:
    """Seal the binary-only Supermemory v0.0.3 lifecycle negative."""

    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(
        experiment.read_bytes()
    ):
        raise EvidenceError("Supermemory result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_supermemory_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "binary-only-native-negative-reproduction",
        "source_id": "supermemory",
        "evidence_grade": "local-negative-reproduced",
        "status": SUPERMEMORY_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/supermemoryai/supermemory": (
                SUPERMEMORY_DOCUMENTATION_REVISION
            ),
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "stable_projection": verified["stable_projection"],
        "execution_identity_sha256s": verified["execution_identities"],
        "claim_boundary": {
            "binary_only": True,
            "h100_admission": "forbidden-for-this-release",
            "local_server_source_available": False,
            "release_revision": SUPERMEMORY_RELEASE_REVISION,
        },
        "files": files,
    }


def seal_graphiti(root: Path, experiment: Path) -> dict[str, Any]:
    """Seal the exact ARM64 FalkorDBLite architecture blocker."""

    files = _capture_files(root)
    experiment_bytes = experiment.read_bytes()
    files["registered-experiment.yaml"] = {
        "bytes": len(experiment_bytes),
        "sha256": _sha256(experiment_bytes),
        "content_base64": base64.b64encode(experiment_bytes).decode("ascii"),
    }
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_graphiti_container_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "graphiti-native-lifecycle-adapter",
        "evidence_grade": "local-negative-reproduced",
        "status": GRAPHITI_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/getzep/graphiti": GRAPHITI_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "module_architecture": verified["module_architecture"],
        "execution_identity_sha256s": verified["execution_identities"],
        "claim_boundary": {
            "container_lifecycle_executed": False,
            "h100_admission": "forbidden-for-this-revision-and-runtime",
            "reason": GRAPHITI_STATUS,
        },
        "files": files,
    }


def seal_magic_context(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(experiment.read_bytes()):
        raise EvidenceError("Magic Context result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_magic_context_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "magic-context",
        "evidence_grade": "local-negative-reproduced",
        "status": MAGIC_CONTEXT_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/cortexkit/magic-context": MAGIC_CONTEXT_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "stable_projection": verified["stable_projection"],
        "execution_identity_sha256s": verified["execution_identities"],
        "files": files,
    }


def seal_gaama(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(experiment.read_bytes()):
        raise EvidenceError("GAAMA result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_gaama_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "matched-component-conformance-reproduction",
        "source_id": "gaama",
        "evidence_grade": "local-conformance-reproduced",
        "status": GAAMA_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/swarna-kpaul/gaama": GAAMA_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "component_summary": verified["component_summary"],
        "execution_identity_sha256s": verified["execution_identities"],
        "files": files,
    }


def seal_gaama_natural(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files_compressed(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(experiment.read_bytes()):
        raise EvidenceError("GAAMA natural result does not bind the registered experiment")
    decoded = _decode_captured_files(files)
    verified = validate_gaama_natural_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "natural-heldout-component-reproduction",
        "source_id": "gaama",
        "evidence_grade": "local-conformance-reproduced",
        "status": GAAMA_NATURAL_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/swarna-kpaul/gaama": GAAMA_REVISION,
        },
        "dataset": {
            "name": "LoCoMo-10",
            "sha256": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
            "license": "CC-BY-NC-4.0",
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "outcome": verified["outcome"],
        "execution_identity_sha256s": verified["execution_identities"],
        "prior_component_receipt": {
            "artifact_path": "research/evidence/memory/gaama-graph-component-v1.json",
            "sha256": "cf903e2bb8444e84d13ef63a13029dc8efc0ed0fea51676a317dbbb9a8d96726",
        },
        "files": files,
    }


def seal_holographic(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(experiment.read_bytes()):
        raise EvidenceError("Holographic result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_holographic_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "hermes-holographic",
        "evidence_grade": "local-negative-reproduced",
        "status": HOLOGRAPHIC_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/NousResearch/hermes-agent": HOLOGRAPHIC_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "stable_projection": verified["stable_projection"],
        "execution_identity_sha256s": verified["execution_identities"],
        "files": files,
    }


def seal_byterover(root: Path, experiment: Path) -> dict[str, Any]:
    files = _capture_files(root)
    if files.get("experiment.yaml", {}).get("sha256") != _sha256(experiment.read_bytes()):
        raise EvidenceError("ByteRover result does not bind the registered experiment")
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_byterover_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "hermes-byterover-cli",
        "evidence_grade": "local-negative-reproduced",
        "status": BYTEROVER_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/NousResearch/hermes-agent": HERMES_REVISION,
            "https://github.com/campfirein/byterover-cli": BYTEROVER_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "manifest_root_sha256": verified["manifest_root"],
        "stable_projection": verified["stable_projection"],
        "execution_identity_sha256s": verified["execution_identities"],
        "files": files,
    }


def seal_openviking(primary: Path, replication: Path, experiment: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for run, root in ((1, primary), (2, replication)):
        captured = _capture_files(root)
        for name, receipt in captured.items():
            files[f"run-{run}/{name}"] = receipt
    experiment_bytes = experiment.read_bytes()
    files["experiment.yaml"] = {
        "bytes": len(experiment_bytes),
        "sha256": _sha256(experiment_bytes),
        "content_base64": base64.b64encode(experiment_bytes).decode("ascii"),
    }
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_openviking_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "openviking",
        "evidence_grade": "local-negative-reproduced",
        "status": OPENVIKING_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/volcengine/OpenViking": OPENVIKING_REVISION,
            "https://github.com/NousResearch/hermes-agent": HERMES_REVISION,
        },
        "runtime_lane": "local-arm64-docker-internal-network",
        "run_count": 2,
        "image_ids": verified["image_ids"],
        "operation_count": verified["operation_count"],
        "state_manifest_sha256s": verified["state_manifest_sha256s"],
        "residue_file_counts": verified["residue_file_counts"],
        "execution_identity_sha256s": verified["execution_identity_sha256s"],
        "files": files,
    }


def seal_mem0_lifecycle(
    root: Path, source_context: Path, image_inspect: Path
) -> dict[str, Any]:
    """Seal two contained Mem0 lifecycle repetitions and their live image receipt."""

    paths: dict[str, Path] = {
        "dockerfile": PROJECT_ROOT
        / "infra"
        / "memory-baselines"
        / "mem0"
        / "Dockerfile.lifecycle-doctor",
        "experiment.yaml": PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-mem0-native-lifecycle-doctor.yaml",
        "image-inspect.json": image_inspect,
        "source-context.json": source_context,
    }
    for name in MEM0_LIFECYCLE_CODE_FILES:
        paths[name] = PROJECT_ROOT / name
    for run in (1, 2):
        paths[f"run-{run}/report.json"] = root / f"run-{run}" / "result" / "report.json"
        paths[f"run-{run}/manifest.json"] = (
            root / f"run-{run}" / "result" / "manifest.json"
        )
        paths[f"run-{run}/stdout.txt"] = root / f"run-{run}.stdout"
        paths[f"run-{run}/stderr.txt"] = root / f"run-{run}.stderr"
    files: dict[str, dict[str, Any]] = {}
    for name, path in sorted(paths.items()):
        if path.is_symlink() or not path.is_file():
            raise EvidenceError(f"Mem0 evidence input is not a regular file: {path}")
        data = path.read_bytes()
        files[name] = {
            "bytes": len(data),
            "sha256": _sha256(data),
            "content_base64": base64.b64encode(data).decode("ascii"),
        }
    decoded = _decode_captured_files(files)
    verified = validate_mem0_lifecycle_files(decoded)
    file_receipts = {
        name: {"bytes": receipt["bytes"], "sha256": receipt["sha256"]}
        for name, receipt in sorted(files.items())
    }
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "mem0-lifecycle-adapter",
        "evidence_grade": "local-negative-reproduced",
        "status": MEM0_LIFECYCLE_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "blocked",
        "reason": (
            "The pinned native Mem0 backend passes bounded CRUD, restart, branch, "
            "lineage, idempotency, and ordinary-scope purge gates, while the "
            "CoTCodec adapter fails closed rather than recovering a crash after "
            "native mutation and leaves the interrupted scope's plaintext canary "
            "in history.db and Qdrant storage.sqlite."
        ),
        "source_revisions": {
            "https://github.com/mem0ai/mem0": MEM0_LIFECYCLE_REVISION,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "stable_projection": verified["stable_projection"],
        "stable_projection_sha256": verified["stable_projection_sha256"],
        "report_sha256s": verified["report_sha256s"],
        "crash_scope_plaintext_proof_roots": verified[
            "crash_scope_plaintext_proof_roots"
        ],
        "source_receipt_sha256": verified["source_receipt_sha256"],
        "files_root_sha256": _sha256(_canonical_json(file_receipts)),
        "files": files,
    }


def seal_hindsight(primary: Path, replication: Path, experiment: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for run, root in ((1, primary), (2, replication)):
        captured = _capture_files(root)
        for name, receipt in captured.items():
            files[f"run-{run}/{name}"] = receipt
    experiment_bytes = experiment.read_bytes()
    files["experiment.yaml"] = {
        "bytes": len(experiment_bytes),
        "sha256": _sha256(experiment_bytes),
        "content_base64": base64.b64encode(experiment_bytes).decode("ascii"),
    }
    decoded = {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in files.items()
    }
    verified = validate_hindsight_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "hermes-hindsight-native",
        "evidence_grade": "local-negative-reproduced",
        "status": HINDSIGHT_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {
            "https://github.com/vectorize-io/hindsight": HINDSIGHT_REVISION,
            "https://github.com/NousResearch/hermes-agent": HERMES_REVISION,
        },
        "runtime_lane": "local-arm64-docker-internal-network",
        "run_count": 2,
        "image_ids": verified["image_ids"],
        "operation_count": verified["operation_count"],
        "state_manifest_sha256s": verified["state_manifest_sha256s"],
        "residue_file_counts": verified["residue_file_counts"],
        "execution_identity_sha256s": verified["execution_identity_sha256s"],
        "files": files,
    }


def _astra_test_projection(payload: dict[str, Any], owner: str) -> list[dict[str, Any]]:
    expected_summary = {
        "numTotalTestSuites": 11,
        "numPassedTestSuites": 11,
        "numFailedTestSuites": 0,
        "numPendingTestSuites": 0,
        "numTotalTests": 26,
        "numPassedTests": 26,
        "numFailedTests": 0,
        "numPendingTests": 0,
        "numTodoTests": 0,
        "success": True,
    }
    if {key: payload.get(key) for key in expected_summary} != expected_summary:
        raise EvidenceError(f"{owner} Vitest summary drifted")
    suites = payload.get("testResults")
    if not isinstance(suites, list) or len(suites) != len(ASTRA_SUITE_COUNTS):
        raise EvidenceError(f"{owner} Vitest suite roster drifted")
    observed_counts: dict[str, int] = {}
    projection: list[dict[str, Any]] = []
    for suite in suites:
        if not isinstance(suite, dict):
            raise EvidenceError(f"{owner} contains an invalid Vitest suite")
        name = suite.get("name")
        if not isinstance(name, str):
            raise EvidenceError(f"{owner} Vitest suite name is invalid")
        normalized_name = name.removeprefix("/work/")
        assertions = suite.get("assertionResults")
        if not isinstance(assertions, list) or suite.get("status") != "passed":
            raise EvidenceError(f"{owner} Vitest suite did not pass")
        observed_counts[normalized_name] = len(assertions)
        for assertion in assertions:
            if not isinstance(assertion, dict):
                raise EvidenceError(f"{owner} contains an invalid assertion")
            if assertion.get("status") != "passed" or assertion.get("failureMessages") != []:
                raise EvidenceError(f"{owner} contains a non-passing assertion")
            ancestors = assertion.get("ancestorTitles")
            if not isinstance(ancestors, list) or not all(
                isinstance(value, str) for value in ancestors
            ):
                raise EvidenceError(f"{owner} assertion ancestry is invalid")
            title = assertion.get("title")
            full_name = assertion.get("fullName")
            if not isinstance(title, str) or not isinstance(full_name, str):
                raise EvidenceError(f"{owner} assertion identity is invalid")
            projection.append(
                {
                    "suite": normalized_name,
                    "ancestors": ancestors,
                    "title": title,
                    "full_name": full_name,
                    "status": "passed",
                }
            )
    if observed_counts != ASTRA_SUITE_COUNTS:
        raise EvidenceError(f"{owner} Vitest assertion roster drifted")
    projection.sort(
        key=lambda row: (row["suite"], row["full_name"], row["title"])
    )
    identities = [(row["suite"], row["full_name"]) for row in projection]
    if len(identities) != len(set(identities)):
        raise EvidenceError(f"{owner} contains duplicate test identities")
    return projection


def validate_astra_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != ASTRA_REQUIRED_FILES:
        raise EvidenceError("ASTRA evidence file roster drifted")
    try:
        inspect_payload = json.loads(files["node-image-inspect.json"])
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvidenceError("ASTRA image inspect is invalid JSON") from exc
    if (
        not isinstance(inspect_payload, list)
        or len(inspect_payload) != 1
        or not isinstance(inspect_payload[0], dict)
    ):
        raise EvidenceError("ASTRA image inspect shape drifted")
    image = inspect_payload[0]
    if (
        image.get("Id") != ASTRA_IMAGE_ID
        or image.get("RepoDigests") != [ASTRA_IMAGE_DIGEST]
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
    ):
        raise EvidenceError("ASTRA image identity drifted")

    projections: list[list[dict[str, Any]]] = []
    run_sha256s: list[str] = []
    for name in ("vitest-run1.json", "vitest-run2.json"):
        payload = _decode_json(files[name], name)
        projections.append(_astra_test_projection(payload, name))
        run_sha256s.append(_sha256(files[name]))
    if projections[0] != projections[1]:
        raise EvidenceError("ASTRA replicated semantic test projection drifted")
    if len(set(run_sha256s)) != 2:
        raise EvidenceError("ASTRA evidence must bind two distinct raw executions")
    projection_sha256 = _sha256(_canonical_json(projections[0]))
    return {
        "image_id": ASTRA_IMAGE_ID,
        "image_digest": ASTRA_IMAGE_DIGEST,
        "projection": projections[0],
        "projection_sha256": projection_sha256,
        "run_sha256s": run_sha256s,
    }


def seal_astra(root: Path) -> dict[str, Any]:
    files = _capture_files(root)
    decoded = _decode_captured_files(files)
    verified = validate_astra_files(decoded)
    return {
        "schema_version": 1,
        "evidence_kind": "active-working-set-component-conformance-reproduction",
        "source_id": "astra-working-set",
        "evidence_grade": "local-conformance-reproduced",
        "status": ASTRA_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {"https://github.com/cyh7789/astra": ASTRA_REVISION},
        "source_receipt": {
            "git_revision": ASTRA_REVISION,
            "git_tree": ASTRA_TREE,
            "git_archive_sha256": ASTRA_ARCHIVE_SHA256,
            "tracked_file_count": 88,
            "license": "MIT",
            "license_sha256": ASTRA_LICENSE_SHA256,
            "package_lock_sha256": ASTRA_LOCK_SHA256,
            "package_json_sha256": ASTRA_PACKAGE_SHA256,
        },
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "shared_image_digest": verified["image_digest"],
        "test_projection_sha256": verified["projection_sha256"],
        "raw_run_sha256s": verified["run_sha256s"],
        "runtime_contract": {
            "dependency_acquisition": "containerized-npm-ci-ignore-scripts",
            "test_network": "none",
            "root_filesystem_read_only": True,
            "capabilities_dropped": "ALL",
            "no_new_privileges": True,
            "sudo_used": False,
            "gpu_count": 0,
        },
        "claim_boundary": {
            "component_tests_reproduced": True,
            "cockroachdb_lifecycle_executed": False,
            "durable_repromotion_executed": False,
            "actor_quality_evaluated": False,
            "h100_admission": "requires-native-lifecycle-and-matched-freeze-first",
        },
        "files": files,
    }


def _publish(payload: dict[str, Any], output: Path) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = _sha256(encoded)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.is_symlink() or output.read_bytes() != encoded:
            raise EvidenceError(f"existing evidence output differs: {output}")
        return digest
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, output)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="kind", required=True)
    total = subparsers.add_parser("total-recall")
    total.add_argument("--primary", type=Path, required=True)
    total.add_argument("--replication", type=Path, required=True)
    total.add_argument("--output", type=Path, required=True)
    allmem = subparsers.add_parser("allmem")
    allmem.add_argument("--root", type=Path, required=True)
    allmem.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-allmem-topology-recovery-doctor.yaml",
    )
    allmem.add_argument("--output", type=Path, required=True)
    mem0_lifecycle = subparsers.add_parser("mem0-lifecycle")
    mem0_lifecycle.add_argument("--root", type=Path, required=True)
    mem0_lifecycle.add_argument("--source-context", type=Path, required=True)
    mem0_lifecycle.add_argument("--image-inspect", type=Path, required=True)
    mem0_lifecycle.add_argument("--output", type=Path, required=True)
    hermes = subparsers.add_parser("hermes")
    hermes.add_argument("--root", type=Path, required=True)
    hermes.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage4-hermes-provider-conformance.yaml",
    )
    hermes.add_argument("--output", type=Path, required=True)
    neo4j = subparsers.add_parser("neo4j")
    neo4j.add_argument("--root", type=Path, required=True)
    neo4j.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-neo4j-preference-supersession-doctor.yaml",
    )
    neo4j.add_argument("--output", type=Path, required=True)
    hippo = subparsers.add_parser("hippo")
    hippo.add_argument("--root", type=Path, required=True)
    hippo.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-hippo-retention-cross-tenant-doctor.yaml",
    )
    hippo.add_argument("--output", type=Path, required=True)
    supermemory = subparsers.add_parser("supermemory")
    supermemory.add_argument("--root", type=Path, required=True)
    supermemory.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage4-supermemory-local-binary-doctor.yaml",
    )
    supermemory.add_argument("--output", type=Path, required=True)
    graphiti = subparsers.add_parser("graphiti")
    graphiti.add_argument("--root", type=Path, required=True)
    graphiti.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-graphiti-native-lifecycle-doctor.yaml",
    )
    graphiti.add_argument("--output", type=Path, required=True)
    magic_context = subparsers.add_parser("magic-context")
    magic_context.add_argument("--root", type=Path, required=True)
    magic_context.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-magic-context-paging-doctor.yaml",
    )
    magic_context.add_argument("--output", type=Path, required=True)
    gaama = subparsers.add_parser("gaama")
    gaama.add_argument("--root", type=Path, required=True)
    gaama.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-gaama-graph-component-doctor.yaml",
    )
    gaama.add_argument("--output", type=Path, required=True)
    gaama_natural = subparsers.add_parser("gaama-natural")
    gaama_natural.add_argument("--root", type=Path, required=True)
    gaama_natural.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage3-gaama-natural-graph-doctor.yaml",
    )
    gaama_natural.add_argument("--output", type=Path, required=True)
    holographic = subparsers.add_parser("holographic")
    holographic.add_argument("--root", type=Path, required=True)
    holographic.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage4-hermes-holographic-lifecycle-doctor.yaml",
    )
    holographic.add_argument("--output", type=Path, required=True)
    byterover = subparsers.add_parser("byterover")
    byterover.add_argument("--root", type=Path, required=True)
    byterover.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage4-hermes-byterover-offline-doctor.yaml",
    )
    byterover.add_argument("--output", type=Path, required=True)
    openviking = subparsers.add_parser("openviking")
    openviking.add_argument("--primary", type=Path, required=True)
    openviking.add_argument("--replication", type=Path, required=True)
    openviking.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage4-hermes-openviking-lifecycle-doctor.yaml",
    )
    openviking.add_argument("--output", type=Path, required=True)
    hindsight = subparsers.add_parser("hindsight")
    hindsight.add_argument("--primary", type=Path, required=True)
    hindsight.add_argument("--replication", type=Path, required=True)
    hindsight.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "memory"
        / "stage4-hermes-hindsight-lifecycle-doctor.yaml",
    )
    hindsight.add_argument("--output", type=Path, required=True)
    astra = subparsers.add_parser("astra")
    astra.add_argument("--root", type=Path, required=True)
    astra.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.kind == "total-recall":
        payload = seal_total_recall(args.primary, args.replication)
    elif args.kind == "allmem":
        payload = seal_allmem(args.root, args.experiment)
    elif args.kind == "mem0-lifecycle":
        payload = seal_mem0_lifecycle(
            args.root, args.source_context, args.image_inspect
        )
    elif args.kind == "hermes":
        payload = seal_hermes(args.root, args.experiment)
    elif args.kind == "neo4j":
        payload = seal_neo4j(args.root, args.experiment)
    elif args.kind == "hippo":
        payload = seal_hippo(args.root, args.experiment)
    elif args.kind == "supermemory":
        payload = seal_supermemory(args.root, args.experiment)
    elif args.kind == "graphiti":
        payload = seal_graphiti(args.root, args.experiment)
    elif args.kind == "magic-context":
        payload = seal_magic_context(args.root, args.experiment)
    elif args.kind == "gaama":
        payload = seal_gaama(args.root, args.experiment)
    elif args.kind == "gaama-natural":
        payload = seal_gaama_natural(args.root, args.experiment)
    elif args.kind == "holographic":
        payload = seal_holographic(args.root, args.experiment)
    elif args.kind == "byterover":
        payload = seal_byterover(args.root, args.experiment)
    elif args.kind == "openviking":
        payload = seal_openviking(args.primary, args.replication, args.experiment)
    elif args.kind == "astra":
        payload = seal_astra(args.root)
    else:
        payload = seal_hindsight(args.primary, args.replication, args.experiment)
    digest = _publish(payload, args.output)
    print(f"sealed memory evidence: {args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
