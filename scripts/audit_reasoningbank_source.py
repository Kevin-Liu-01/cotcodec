#!/usr/bin/env python3
"""Audit a pinned ReasoningBank checkout without importing provider code."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_reasoningbank_source_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_FINDINGS,
    EXPECTED_SOURCE,
    validate_experiment_contract,
)

DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "raw" / "baselines" / "reasoning-bank"

SOURCE_MARKERS = {
    "WebArena/memory_management.py": (
        "vertexai.init(",
        "client = genai.Client(vertexai=True)",
        "AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-8B'",
        'with open(cache_path, "a") as f:',
        "instruct_vec = embed_query_with_gemini",
    ),
    "WebArena/pipeline_memory.py": (
        "# step 1: run inference",
        "# step 2: run evaluation",
        "# step 3: extract new memory items",
    ),
    "WebArena/induce_memory.py": (
        "pickle.load(fh)",
        "except Exception:",
        "temperature=1.0",
        "with open(args.output_path, 'a') as f:",
    ),
    "WebArena/pipeline_scaling.py": (
        "for i in range(args.num_trials):",
        '"--result_dir", f"{args.output_dir}/results_{i}",',
    ),
    "WebArena/induce_scaling.py": (
        "if reward == 0:",
        'status = "success"',
        'status = "fail"',
    ),
    "third_party/src/minisweagent/run/extra/swebench.py": (
        "client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))",
        'cache_path=f"./memory/{model.config.model_name}_embeddings.jsonl"',
        'with open(f"./memory/{model.config.model_name}.jsonl", "a") as f:',
        "ThreadPoolExecutor(max_workers=workers)",
    ),
    "third_party/src/minisweagent/memory/memory_management.py": (
        "client = genai.Client()",
        "AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-8B'",
        'with open(cache_path, "a") as f:',
    ),
}


class ReasoningBankSourceAuditError(ValueError):
    """Raised when source evidence does not match the registered checkout."""


def _run_git(source_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=source_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_archive_sha256(source_root: Path, revision: str) -> str:
    process = subprocess.Popen(
        ["git", "archive", "--format=tar", revision],
        cwd=source_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise ReasoningBankSourceAuditError("git archive did not expose stdout")
    digest = hashlib.sha256()
    for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
        digest.update(chunk)
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.wait() != 0:
        raise ReasoningBankSourceAuditError(f"git archive failed: {stderr.strip()}")
    return digest.hexdigest()


def _regular_file(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ReasoningBankSourceAuditError(f"critical source is not regular: {relative}")
    return path


def audit_source(
    source_root: Path,
    *,
    expected_source: dict[str, Any] = EXPECTED_SOURCE,
) -> dict[str, Any]:
    source_root = source_root.resolve(strict=True)
    if not source_root.is_dir():
        raise ReasoningBankSourceAuditError("source root is not a directory")
    try:
        revision = _run_git(source_root, "rev-parse", "HEAD")
        tree = _run_git(source_root, "rev-parse", "HEAD^{tree}")
        dirty = _run_git(source_root, "status", "--porcelain=v1")
    except subprocess.CalledProcessError as exc:
        raise ReasoningBankSourceAuditError("source root is not a valid Git checkout") from exc
    if revision != expected_source["revision"] or tree != expected_source["tree"]:
        raise ReasoningBankSourceAuditError("ReasoningBank revision or tree drifted")
    if dirty:
        raise ReasoningBankSourceAuditError("ReasoningBank checkout is dirty")
    archive_sha256 = _git_archive_sha256(source_root, revision)
    if archive_sha256 != expected_source["git_archive_tar_sha256"]:
        raise ReasoningBankSourceAuditError("ReasoningBank archive SHA-256 drifted")

    file_sha256s: dict[str, str] = {}
    expected_files = {
        "LICENSE": expected_source["license_sha256"],
        "pyproject.toml": expected_source["pyproject_sha256"],
        "uv.lock": expected_source["uv_lock_sha256"],
        **expected_source["critical_file_sha256s"],
    }
    for relative, expected_sha256 in expected_files.items():
        path = _regular_file(source_root, relative)
        file_sha256s[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        if file_sha256s[relative] != expected_sha256:
            raise ReasoningBankSourceAuditError(f"source SHA-256 drifted: {relative}")

    marker_receipts: dict[str, list[str]] = {}
    for relative, markers in SOURCE_MARKERS.items():
        text = _regular_file(source_root, relative).read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise ReasoningBankSourceAuditError(
                f"registered source finding no longer holds in {relative}: {missing}"
            )
        marker_receipts[relative] = [
            hashlib.sha256(marker.encode("utf-8")).hexdigest() for marker in markers
        ]

    experiment = validate_experiment_contract()
    return {
        "schema_version": 1,
        "source_id": "reasoningbank",
        "evidence_kind": "source-admission-audit",
        "status": "BLOCKED_MUTABLE_EVALUATION_AND_UNPINNED_RETRIEVAL",
        "scientific_result": False,
        "publication_ready": False,
        "source_revisions": {expected_source["repository"]: revision},
        "source_tree": tree,
        "git_archive_tar_sha256": archive_sha256,
        "file_sha256s": file_sha256s,
        "finding_marker_sha256s": marker_receipts,
        "findings": EXPECTED_FINDINGS,
        "experiment_sha256": hashlib.sha256(DEFAULT_EXPERIMENT.read_bytes()).hexdigest(),
        "h100_admission": experiment["admission"]["h100_admission"],
    }


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_source(args.source_root)
    if args.output is not None:
        _write_new(args.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
