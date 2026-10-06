#!/usr/bin/env python3
"""Build and run the natural held-out GAAMA graph doctor in Docker."""

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

from scripts.validate_gaama_natural_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    VALID_STATUSES,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra/memory-baselines/gaama-natural"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/results/gaama-natural/2026-08-14-doctor-v1"
DEFAULT_IMAGE_TAG = "cotcodec-gaama-natural-doctor:2d992f7-arm64-v1"


class DoctorError(RuntimeError):
    """Raised when source, containment, or natural-study semantics drift."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise DoctorError(f"expected regular file: {path}")
    return _sha(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _run(argv: list[str], *, cwd: Path | None = None, timeout: int = 1200) -> bytes:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise DoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    return completed.stdout


def _strict_json(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise DoctorError(f"{owner} contains non-finite JSON constant {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"{owner} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{owner} must be a JSON object")
    return payload


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


def _extract(archive: bytes, destination: Path) -> None:
    seen: set[str] = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > 20_000:
            raise DoctorError("GAAMA archive member count is invalid")
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise DoctorError(f"unsafe archive path: {member.name}")
            name = relative.as_posix()
            if name in seen:
                raise DoctorError(f"duplicate archive path: {name}")
            seen.add(name)
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise DoctorError(f"unsupported archive member: {name}")
            total += member.size
            if total > 512 * 1024 * 1024:
                raise DoctorError("GAAMA archive exceeds the byte ceiling")
            source = bundle.extractfile(member)
            if source is None:
                raise DoctorError(f"archive member has no bytes: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
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
    revision = _run(["git", "rev-parse", "HEAD"], cwd=checkout).decode().strip()
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout).decode().strip()
    if revision != source["revision"] or tree != source["tree"]:
        raise DoctorError("GAAMA Git identity drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout).strip():
        raise DoctorError("GAAMA checkout is dirty")
    archive = _run(["git", "archive", "--format=tar", "HEAD"], cwd=checkout)
    checks = {
        "git_archive_tar_sha256": _sha(archive),
        "license_sha256": _sha_path(checkout / "LICENSE"),
        "pagerank_sha256": _sha_path(checkout / "services/pagerank.py"),
        "retriever_sha256": _sha_path(checkout / "services/ltm_retriever.py"),
        "locomo10_sha256": _sha_path(checkout / "evals/locomo/locomo10.json"),
    }
    if any(checks[field] != source[field] for field in checks):
        raise DoctorError("GAAMA source file receipt drifted")
    context = root / "context"
    upstream = context / "upstream"
    upstream.mkdir(parents=True)
    _extract(archive, upstream)
    (context / "harness/memory_trials").mkdir(parents=True)
    copied = (
        "gaama_component.py",
        "gaama_natural.py",
    )
    for name in copied:
        shutil.copy2(
            PROJECT_ROOT / "harness/memory_trials" / name,
            context / "harness/memory_trials" / name,
        )
    _write_once(context / "harness/__init__.py", b"")
    _write_once(context / "harness/memory_trials/__init__.py", b"")
    shutil.copy2(DOCTOR_ROOT / "Dockerfile", context / "Dockerfile")
    shutil.copy2(DOCTOR_ROOT / "doctor.py", context / "doctor.py")
    return {
        "context": context,
        "repository": source["repository"],
        "revision": revision,
        "tree": tree,
        **checks,
        "worktree_clean": True,
        "archive_bytes": len(archive),
        "component_sha256": _sha_path(
            PROJECT_ROOT / "harness/memory_trials/gaama_component.py"
        ),
        "natural_module_sha256": _sha_path(
            PROJECT_ROOT / "harness/memory_trials/gaama_natural.py"
        ),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.py"),
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
    }


def _build_image(
    experiment: dict[str, Any], source: dict[str, Any], image_tag: str
) -> dict[str, Any]:
    runtime = experiment["runtime"]
    _run(
        [
            "docker",
            "build",
            "--platform",
            runtime["local_platform"],
            "--build-arg",
            f"BASE_IMAGE={runtime['base_image']}",
            "--build-arg",
            f"COTCODEC_GAAMA_GIT_SHA={experiment['source']['revision']}",
            "--build-arg",
            f"COTCODEC_GAAMA_SOURCE_SHA256={experiment['source']['git_archive_tar_sha256']}",
            "--tag",
            image_tag,
            str(source["context"]),
        ],
        timeout=1200,
    )
    raw = _run(["docker", "image", "inspect", image_tag])
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError("Docker inspect must return one image")
    inspect = rows[0]
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != runtime["user"]
        or labels.get("org.opencontainers.image.revision") != experiment["source"]["revision"]
        or labels.get("org.cotcodec.source-archive-sha256")
        != experiment["source"]["git_archive_tar_sha256"]
    ):
        raise DoctorError("GAAMA natural image contract drifted")
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise DoctorError("GAAMA natural image ID is invalid")
    return {"image_id": image_id, "inspect": inspect, "inspect_sha256": _sha(raw)}


def _execute(image_id: str, run: int, runtime: dict[str, Any]) -> tuple[list[str], bytes]:
    argv = [
        "docker",
        "run",
        "--rm",
        "--name",
        f"cotcodec-gaama-natural-{os.getpid()}-{run}",
        "--pull=never",
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
        str(runtime["cpu_limit"]),
        "--memory",
        str(runtime["memory_limit"]),
        image_id,
    ]
    return argv, _run(argv, timeout=runtime["timeout_seconds"])


def _validate_report(report: dict[str, Any], experiment: dict[str, Any]) -> None:
    contract = experiment["contract"]
    report_hash = report.get("report_sha256")
    without_hash = {key: value for key, value in report.items() if key != "report_sha256"}
    integrity = report.get("integrity_gates")
    graph_gates = report.get("graph_gates")
    dev_rows = report.get("dev_rows")
    rows = report.get("rows")
    arm_names = {
        "flat",
        "ppr_weight_zero",
        "true_graph",
        "shuffled_graph_seed_42",
        "shuffled_graph_seed_43",
        "shuffled_graph_seed_44",
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != experiment["study_id"]
        or report.get("status") not in VALID_STATUSES
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("dataset_sha256") != experiment["source"]["locomo10_sha256"]
        or report.get("dev_sample_ids") != contract["dev_sample_ids"]
        or report.get("test_sample_ids") != contract["test_sample_ids"]
        or report.get("dev_questions") != contract["expected_dev_questions"]
        or report.get("test_questions") != contract["expected_test_questions"]
        or report.get("dialogue_nodes") != contract["expected_dialogue_nodes"]
        or report.get("primary_metric") != "evidence_recall_all_at_10"
        or report.get("selected_ppr_weight") not in contract["ppr_weights"]
        or report.get("model_calls") != 0
        or report.get("embedding_calls") != 0
        or report.get("network_calls") != 0
        or not isinstance(integrity, dict)
        or not all(integrity.values())
        or not isinstance(graph_gates, dict)
        or set(graph_gates)
        != {
            "selected_nonzero_weight",
            "true_minus_flat_at_least_one_point",
            "clustered_ci_excludes_zero",
            "true_minus_mean_shuffled_at_least_one_point",
            "one_sided_sign_randomization_below_0_05",
            "shuffled_clustered_ci_excludes_zero",
            "shuffled_one_sided_sign_randomization_below_0_05",
        }
        or not isinstance(rows, dict)
        or set(rows) != arm_names
        or any(len(rows[name]) != contract["expected_test_questions"] for name in arm_names)
        or not isinstance(dev_rows, dict)
        or set(dev_rows) != {str(weight) for weight in contract["ppr_weights"]}
        or any(
            len(dev_rows[str(weight)]) != contract["expected_dev_questions"]
            for weight in contract["ppr_weights"]
        )
        or report_hash != _sha(_json_bytes(without_hash))
    ):
        raise DoctorError("GAAMA natural report contract drifted")
    rosters = [tuple(row["question_id"] for row in rows[name]) for name in sorted(arm_names)]
    if len(set(rosters)) != 1:
        raise DoctorError("GAAMA natural arm rosters drifted")
    dev_rosters = [
        tuple(row["question_id"] for row in dev_rows[str(weight)])
        for weight in contract["ppr_weights"]
    ]
    if len(set(dev_rosters)) != 1:
        raise DoctorError("GAAMA natural dev-weight rosters drifted")
    graph_pass = all(graph_gates.values())
    expected_status = "GAAMA_NATURAL_GRAPH_PASS" if graph_pass else "GAAMA_NATURAL_GRAPH_KILLED"
    expected_h100 = "eligible-for-separate-design-review" if graph_pass else "blocked"
    if report["status"] != expected_status or report.get("h100_admission") != expected_h100:
        raise DoctorError("GAAMA natural outcome classification drifted")


def _manifest(root: Path, status: str) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise DoctorError(f"output contains symlink: {path}")
        if path.is_file() and path.name != "manifest.json":
            data = path.read_bytes()
            files[path.relative_to(root).as_posix()] = {"bytes": len(data), "sha256": _sha(data)}
    return {
        "schema_version": 1,
        "status": status,
        "files": files,
        "root_sha256": _sha(_json_bytes(files)),
    }


def run(experiment_path: Path, output: Path, image_tag: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    if output.exists():
        raise DoctorError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        with tempfile.TemporaryDirectory(prefix="cotcodec-gaama-natural-build-") as build_dir:
            source = _prepare_context(Path(build_dir), experiment)
            image = _build_image(experiment, source, image_tag)
            dataset_bytes = (
                source["context"] / "upstream/evals/locomo/locomo10.json"
            ).read_bytes()
            source.pop("context")
            _write_once(temp_output / "experiment.yaml", experiment_path.read_bytes())
            _write_once(temp_output / "source/locomo10.json", dataset_bytes)
            _write_once(temp_output / "source-receipt.json", _json_bytes(source))
            _write_once(temp_output / "image-inspect.json", _json_bytes(image["inspect"]))
            reports: list[dict[str, Any]] = []
            for index in range(1, experiment["runtime"]["clean_repetitions"] + 1):
                argv, raw = _execute(image["image_id"], index, experiment["runtime"])
                report = _strict_json(raw, f"run-{index}")
                _validate_report(report, experiment)
                reports.append(report)
                _write_once(temp_output / f"run-{index}/argv.json", _json_bytes(argv))
                _write_once(temp_output / f"run-{index}/report.json", _json_bytes(report))
            if reports[0] != reports[1]:
                raise DoctorError("GAAMA natural clean repetitions differ")
            result = reports[0]
            summary = {
                "schema_version": 1,
                "study": experiment["study_id"],
                "status": result["status"],
                "scientific_result": False,
                "publication_ready": False,
                "run_count": 2,
                "source": source,
                "image": {
                    "image_id": image["image_id"],
                    "inspect_sha256": image["inspect_sha256"],
                },
                "natural_report_sha256": result["report_sha256"],
                "outcome": {
                    "selected_ppr_weight": result["selected_ppr_weight"],
                    "test_questions": result["test_questions"],
                    "arm_summaries": result["arm_summaries"],
                    "primary_comparison": result["primary_comparison"],
                    "integrity_gates": result["integrity_gates"],
                    "graph_gates": result["graph_gates"],
                },
                "admission": {
                    "natural_heldout_component": (
                        "pass" if result["status"] == "GAAMA_NATURAL_GRAPH_PASS" else "killed"
                    ),
                    "h100": result["h100_admission"],
                },
            }
            _write_once(temp_output / "report.json", _json_bytes(summary))
            manifest = _manifest(temp_output, result["status"])
            _write_once(temp_output / "manifest.json", _json_bytes(manifest))
            os.rename(temp_output, output)
            return summary
    except Exception:
        shutil.rmtree(temp_output, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    args = parser.parse_args()
    summary = run(args.experiment, args.output, args.image_tag)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
