#!/usr/bin/env python3
"""Build and run the pinned All-Mem topology-recovery doctor in Docker."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_allmem_topology_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "all-mem"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "results" / "allmem-topology" / "2026-08-15-doctor-v4"
)
DEFAULT_IMAGE_TAG = "cotcodec-allmem-topology-doctor:f5d6912-arm64-v1"
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024


class AllMemDoctorError(RuntimeError):
    """Raised when source, containment, execution, or evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise AllMemDoctorError(f"expected regular file: {path}")
    return _sha(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _semantic_projection(projection: dict[str, Any]) -> dict[str, Any]:
    """Normalize retrieval ties without hiding topology or content drift."""

    normalized = json.loads(json.dumps(projection))
    normalized.pop("sha256", None)
    source_content = {
        row["source_id"]: row["content_sha256"]
        for row in normalized.get("nodes", [])
        if row.get("source_id") is not None
    }
    query = normalized.get("query", {})
    ranked = query.pop("ranked_source_ids", [])
    query["ranked_content_sha256"] = [
        source_content.get(source_id, f"missing:{source_id}") for source_id in ranked
    ]
    return normalized


def _semantic_projection_sha256(projection: dict[str, Any]) -> str:
    return _sha(
        json.dumps(
            _semantic_projection(projection), separators=(",", ":"), sort_keys=True
        ).encode()
    )


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 1_200,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise AllMemDoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    return completed


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise AllMemDoctorError(f"{label} contains non-finite value: {value}")

    try:
        value = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AllMemDoctorError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AllMemDoctorError(f"{label} must be a JSON object")
    return value


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
                raise AllMemDoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _extract_archive(archive: bytes, destination: Path) -> None:
    total = 0
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            raise AllMemDoctorError("All-Mem archive member count is invalid")
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise AllMemDoctorError(f"unsafe All-Mem archive path: {member.name}")
            name = relative.as_posix()
            if name in seen:
                raise AllMemDoctorError(f"duplicate All-Mem archive path: {name}")
            seen.add(name)
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise AllMemDoctorError(f"unsupported All-Mem archive member: {name}")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise AllMemDoctorError("All-Mem archive exceeds byte ceiling")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise AllMemDoctorError(f"All-Mem archive member has no bytes: {name}")
            with target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(member.mode & 0o777)


def _prepare_context(root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    checkout = root / "checkout"
    _run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            source["repository"],
            str(checkout),
        ]
    )
    _run(["git", "checkout", "--detach", source["revision"]], cwd=checkout)
    revision = _run(["git", "rev-parse", "HEAD"], cwd=checkout).stdout.decode().strip()
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout).stdout.decode().strip()
    if revision != source["revision"] or tree != source["tree"]:
        raise AllMemDoctorError("All-Mem Git identity drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout).stdout.strip():
        raise AllMemDoctorError("All-Mem checkout is dirty")
    archive = _run(["git", "archive", "--format=tar", "HEAD"], cwd=checkout).stdout
    expected_files = {
        "LICENSE": source["license_sha256"],
        "requirements.txt": source["requirements_sha256"],
        "all_mem/core.py": source["core_sha256"],
        "all_mem/llm.py": source["llm_sha256"],
    }
    if _sha(archive) != source["git_archive_tar_sha256"]:
        raise AllMemDoctorError("All-Mem source archive drifted")
    for name, expected in expected_files.items():
        if _sha_path(checkout / name) != expected:
            raise AllMemDoctorError(f"All-Mem source file drifted: {name}")

    context = root / "context"
    upstream = context / "upstream"
    upstream.mkdir(parents=True)
    _extract_archive(archive, upstream)
    shutil.copy2(DOCTOR_ROOT / "Dockerfile", context / "Dockerfile")
    shutil.copy2(DOCTOR_ROOT / "doctor.py", context / "doctor.py")
    return {
        "context": context,
        "repository": source["repository"],
        "revision": revision,
        "tree": tree,
        "git_archive_tar_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "verified_files": expected_files,
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.py"),
        "worktree_clean": True,
    }


def _build_image(
    experiment: dict[str, Any], source: dict[str, Any], image_tag: str
) -> tuple[dict[str, Any], bytes]:
    runtime = experiment["runtime"]
    _run(
        [
            "docker",
            "build",
            "--platform",
            runtime["platform"],
            "--build-arg",
            f"BASE_IMAGE={runtime['base_image']}",
            "--build-arg",
            f"COTCODEC_ALLMEM_GIT_SHA={experiment['source']['revision']}",
            "--build-arg",
            (
                "COTCODEC_ALLMEM_SOURCE_SHA256="
                f"{experiment['source']['git_archive_tar_sha256']}"
            ),
            "--tag",
            image_tag,
            str(source["context"]),
        ],
        timeout=1_800,
    )
    inspect_raw = _run(["docker", "image", "inspect", image_tag]).stdout
    rows = _strict_json(inspect_raw, "docker inspect") if inspect_raw.startswith(b"{") else None
    if rows is not None:
        raise AllMemDoctorError("docker inspect unexpectedly returned an object")
    try:
        parsed = json.loads(inspect_raw)
    except json.JSONDecodeError as exc:
        raise AllMemDoctorError("docker inspect is invalid") from exc
    if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
        raise AllMemDoctorError("docker inspect must contain one image")
    inspect = parsed[0]
    labels = inspect.get("Config", {}).get("Labels", {})
    expected_labels = {
        "org.opencontainers.image.source": experiment["source"]["repository"],
        "org.opencontainers.image.revision": experiment["source"]["revision"],
        "org.cotcodec.source-archive-sha256": experiment["source"][
            "git_archive_tar_sha256"
        ],
        "org.cotcodec.experiment": "allmem-topology-recovery-v1",
        "org.cotcodec.publication-ready": "false",
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise AllMemDoctorError("All-Mem image labels drifted")
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise AllMemDoctorError("All-Mem image ID is invalid")
    return (
        {
            "image_tag": image_tag,
            "image_id": image_id,
            "inspect_sha256": _sha(inspect_raw),
            "labels": expected_labels,
        },
        inspect_raw,
    )


def _validate_phase(payload: dict[str, Any], phase: str) -> dict[str, Any]:
    if (
        payload.get("phase") != phase
        or payload.get("status") != EXPECTED_STATUS
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("external_model_calls") != 0
    ):
        raise AllMemDoctorError(f"All-Mem {phase} identity drifted")
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        raise AllMemDoctorError(f"All-Mem {phase} projection is missing")
    expected_recovery = {
        "update": True,
        "split": False,
        "merge_a": False,
        "merge_b": False,
    }
    if (
        projection.get("recovery") != expected_recovery
        or projection.get("derived_source_labels_without_raw_path") is not True
        or projection.get("native_scoped_purge") is not False
        or projection.get("persistence_format") != "pickle"
        or projection.get("query", {}).get("update_old_recovered") is not True
        or projection.get("query", {}).get("update_new_recovered") is not True
    ):
        raise AllMemDoctorError(f"All-Mem {phase} falsifier drifted")
    projection_sha = projection.get("sha256")
    projection_without_sha = dict(projection)
    projection_without_sha.pop("sha256", None)
    canonical = json.dumps(
        projection_without_sha, separators=(",", ":"), sort_keys=True
    ).encode()
    if projection_sha != _sha(canonical):
        raise AllMemDoctorError(f"All-Mem {phase} projection hash drifted")
    return projection


def _run_phase(
    experiment: dict[str, Any], image_tag: str, state: Path, phase: str
) -> tuple[dict[str, Any], bytes, list[str]]:
    runtime = experiment["runtime"]
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        runtime["platform"],
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        str(runtime["max_cpu_cores"]),
        "--memory",
        f"{runtime['max_memory_mib']}m",
        "--pids-limit",
        "256",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--volume",
        f"{state / 'graph.pkl'}:/state/graph.pkl:rw",
        image_tag,
        "--phase",
        phase,
    ]
    completed = _run(argv, timeout=runtime["wall_clock_minutes"] * 60)
    payload = _strict_json(completed.stdout, f"All-Mem {phase}")
    _validate_phase(payload, phase)
    return payload, completed.stderr, argv


def run_doctor(
    *,
    experiment_path: Path = DEFAULT_EXPERIMENT,
    output_dir: Path = DEFAULT_OUTPUT,
    image_tag: str = DEFAULT_IMAGE_TAG,
) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    if output_dir.exists() and (output_dir.is_symlink() or any(output_dir.iterdir())):
        raise AllMemDoctorError("output directory must be absent or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise AllMemDoctorError("output directory cannot be a symlink")

    # Keep bind-mounted state below the selected result root. Docker Desktop
    # does not project macOS /var/folders temporary files as regular files.
    with tempfile.TemporaryDirectory(
        prefix=".cotcodec-allmem-doctor-", dir=output_dir.parent
    ) as temp:
        work = Path(temp)
        source = _prepare_context(work, experiment)
        image, inspect_raw = _build_image(experiment, source, image_tag)
        source_public = dict(source)
        source_public.pop("context")
        evidence_inputs = {
            "experiment.yaml": experiment_path.read_bytes(),
            "Dockerfile": (DOCTOR_ROOT / "Dockerfile").read_bytes(),
            "doctor.py": (DOCTOR_ROOT / "doctor.py").read_bytes(),
            "run_allmem_topology_doctor.py": Path(__file__).read_bytes(),
            "validate_allmem_topology_experiment.py": (
                PROJECT_ROOT / "scripts" / "validate_allmem_topology_experiment.py"
            ).read_bytes(),
            "image-inspect.json": inspect_raw,
            "source-receipt.json": _json_bytes(source_public),
        }
        for name, data in evidence_inputs.items():
            _write_once(output_dir / name, data)
        repeats = []
        observed_rank_orders: set[tuple[str, ...]] = set()
        for index in range(1, experiment["runtime"]["clean_state_repeats"] + 1):
            state = work / f"state-{index}"
            state.mkdir()
            state_file = state / "graph.pkl"
            state_file.touch(mode=0o666)
            # The image runs as uid 65532. Bind only a fresh writable file; the
            # container has no authority to create sibling host paths.
            state_file.chmod(0o666)
            prepare, prepare_stderr, prepare_argv = _run_phase(
                experiment, image_tag, state, "prepare"
            )
            verify, verify_stderr, verify_argv = _run_phase(
                experiment, image_tag, state, "verify"
            )
            prepare_semantic_sha = _semantic_projection_sha256(prepare["projection"])
            verify_semantic_sha = _semantic_projection_sha256(verify["projection"])
            if prepare_semantic_sha != verify_semantic_sha:
                raise AllMemDoctorError(
                    "fresh-container semantic projection drifted: "
                    + json.dumps(
                        {
                            "prepare": _semantic_projection(prepare["projection"]),
                            "verify": _semantic_projection(verify["projection"]),
                        },
                        sort_keys=True,
                    )
                )
            prepare_order = tuple(prepare["projection"]["query"]["ranked_source_ids"])
            verify_order = tuple(verify["projection"]["query"]["ranked_source_ids"])
            observed_rank_orders.update((prepare_order, verify_order))
            run_root = output_dir / f"run-{index}"
            _write_once(run_root / "prepare.json", _json_bytes(prepare))
            _write_once(run_root / "verify.json", _json_bytes(verify))
            _write_once(run_root / "prepare.argv.json", _json_bytes(prepare_argv))
            _write_once(run_root / "verify.argv.json", _json_bytes(verify_argv))
            _write_once(run_root / "prepare.stderr", prepare_stderr)
            _write_once(run_root / "verify.stderr", verify_stderr)
            _write_once(run_root / "graph.pkl", state_file.read_bytes())
            repeats.append(
                {
                    "run": index,
                    "prepare_sha256": _sha_path(run_root / "prepare.json"),
                    "verify_sha256": _sha_path(run_root / "verify.json"),
                    "prepare_projection_sha256": prepare["projection"]["sha256"],
                    "verify_projection_sha256": verify["projection"]["sha256"],
                    "semantic_projection_sha256": prepare_semantic_sha,
                    "exact_projection_equal": (
                        prepare["projection"] == verify["projection"]
                    ),
                    "prepare_ranked_source_ids": list(prepare_order),
                    "verify_ranked_source_ids": list(verify_order),
                    "state_file_sha256": _sha_path(state / "graph.pkl"),
                }
            )
        if len({row["semantic_projection_sha256"] for row in repeats}) != 1:
            raise AllMemDoctorError("clean-state semantic projection repetitions drifted")

        report = {
            "schema_version": 1,
            "source_id": "all-mem",
            "status": EXPECTED_STATUS,
            "evidence_kind": "native-negative-reproduction",
            "scientific_result": False,
            "publication_ready": False,
            "runtime_lane": "local-arm64-docker-network-none",
            "run_count": len(repeats),
            "source_revisions": {
                experiment["source"]["repository"]: experiment["source"]["revision"]
            },
            "source": source_public,
            "container": image,
            "native_projection_example": prepare["projection"],
            "stable_semantic_projection_sha256": repeats[0][
                "semantic_projection_sha256"
            ],
            "fresh_restart_exact_projection_equal_all": all(
                row["exact_projection_equal"] for row in repeats
            ),
            "observed_rank_orders": [list(order) for order in sorted(observed_rank_orders)],
            "runs": repeats,
            "claim_boundary": {
                "active_anchor_and_update_expansion_executed": True,
                "split_merge_raw_recovery_failed": True,
                "external_model_calls": 0,
                "memory_quality_measured": False,
                "graph_efficacy_measured": False,
                "active_inactive_paging_measured": False,
                "semantic_restart_projection_stable": True,
                "exact_tie_order_stability_claimed": False,
                "h100_admission": "forbidden-for-this-revision",
            },
        }
        _write_once(output_dir / "report.json", _json_bytes(report))
        files = {}
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                files[path.relative_to(output_dir).as_posix()] = {
                    "bytes": path.stat().st_size,
                    "sha256": _sha_path(path),
                }
        manifest = {
            "schema_version": 1,
            "status": "SEALED_ALLMEM_TOPOLOGY_NEGATIVE",
            "source_id": "all-mem",
            "report_sha256": _sha_path(output_dir / "report.json"),
            "files": files,
        }
        _write_once(output_dir / "manifest.json", _json_bytes(manifest))
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    args = parser.parse_args()
    report = run_doctor(
        experiment_path=args.experiment,
        output_dir=args.output_dir,
        image_tag=args.image_tag,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
