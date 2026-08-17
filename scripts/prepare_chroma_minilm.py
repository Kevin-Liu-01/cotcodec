#!/usr/bin/env python3
"""Acquire or verify Chroma's pinned ONNX MiniLM artifact for offline runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.mempalace_control import (  # noqa: E402
    MEMPALACE_MINILM_ARCHIVE_SHA256,
    MEMPALACE_MINILM_ARCHIVE_URL,
    MEMPALACE_MINILM_DIMENSIONS,
    MEMPALACE_MINILM_MAXIMUM_TOKENS,
    MEMPALACE_MINILM_MODEL,
    MEMPALACE_MINILM_POOLING,
)

EXPECTED_MODEL_FILES = (
    "onnx/config.json",
    "onnx/model.onnx",
    "onnx/special_tokens_map.json",
    "onnx/tokenizer.json",
    "onnx/tokenizer_config.json",
    "onnx/vocab.txt",
)
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
RECEIPT_NAME = "cotcodec-minilm-receipt.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _download(destination: Path, *, url: str) -> None:
    request = urllib.request.Request(  # noqa: S310 - fixed HTTPS URL, hash verified
        url, headers={"User-Agent": "cotcodec-artifact-prestage/1"}
    )
    total = 0
    with urllib.request.urlopen(request, timeout=120) as response, destination.open(
        "xb", buffering=0
    ) as output:  # noqa: S310 - see fixed URL and SHA above
        final_url = response.geturl()
        if not final_url.startswith("https://"):
            raise ValueError("MiniLM download redirected outside HTTPS")
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("MiniLM archive exceeds the 512 MiB ceiling")
            output.write(chunk)
        os.fsync(output.fileno())


def _extract_exact_archive(archive: Path, destination: Path) -> None:
    expected = set(EXPECTED_MODEL_FILES)
    seen: set[str] = set()
    try:
        with tarfile.open(archive, mode="r:gz") as bundle:
            for member in bundle.getmembers():
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("MiniLM archive contains path traversal")
                normalized = path.as_posix().lstrip("./")
                if member.isdir():
                    if normalized not in {"onnx", ""}:
                        raise ValueError("MiniLM archive contains an unexpected directory")
                    continue
                if not member.isfile() or normalized not in expected or normalized in seen:
                    raise ValueError("MiniLM archive contains an unexpected or duplicate member")
                source = bundle.extractfile(member)
                if source is None:
                    raise ValueError("MiniLM archive member cannot be read")
                target = destination / normalized
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb", buffering=0) as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                    os.fsync(output.fileno())
                os.chmod(target, 0o644)
                seen.add(normalized)
    except (tarfile.TarError, OSError) as exc:
        raise ValueError("MiniLM archive cannot be safely extracted") from exc
    if seen != expected:
        raise ValueError("MiniLM archive does not contain the exact required file roster")


def _file_manifest(root: Path) -> list[dict[str, Any]]:
    files = []
    for relative in EXPECTED_MODEL_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"MiniLM artifact file is missing or unsafe: {relative}")
        files.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return files


def _validate_complete_tree_roster(root: Path) -> None:
    expected_files = {*EXPECTED_MODEL_FILES, "onnx.tar.gz", RECEIPT_NAME}
    expected_directories = {"onnx"}
    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError("MiniLM artifact tree contains a symbolic link")
        if path.is_file():
            observed_files.add(relative)
        elif path.is_dir():
            observed_directories.add(relative)
        else:
            raise ValueError("MiniLM artifact tree contains an unsupported entry")
    if observed_files != expected_files or observed_directories != expected_directories:
        raise ValueError("MiniLM artifact tree roster drifted")


def _receipt(*, files: list[dict[str, Any]], archive_sha256: str) -> dict[str, Any]:
    tree_sha256 = hashlib.sha256(_canonical(files).encode()).hexdigest()
    unsigned = {
        "schema_version": 1,
        "status": "VERIFIED_CHROMA_MINILM_ARTIFACT",
        "model": MEMPALACE_MINILM_MODEL,
        "source_url": MEMPALACE_MINILM_ARCHIVE_URL,
        "archive_sha256": archive_sha256,
        "dimensions": MEMPALACE_MINILM_DIMENSIONS,
        "maximum_tokens": MEMPALACE_MINILM_MAXIMUM_TOKENS,
        "pooling_strategy": MEMPALACE_MINILM_POOLING,
        "files": files,
        "artifact_root_sha256": tree_sha256,
    }
    return {
        **unsigned,
        "receipt_sha256": hashlib.sha256(_canonical(unsigned).encode()).hexdigest(),
    }


def verify_prepared_artifact(
    output_dir: Path,
    *,
    expected_archive_sha256: str = MEMPALACE_MINILM_ARCHIVE_SHA256,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    receipt_path = output_dir / RECEIPT_NAME
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise ValueError("MiniLM receipt is missing or unsafe")
    try:
        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("MiniLM receipt is not valid JSON") from exc
    files = _file_manifest(output_dir)
    expected = _receipt(files=files, archive_sha256=expected_archive_sha256)
    if stored != expected:
        raise ValueError("MiniLM receipt differs from the prepared artifact")
    _validate_complete_tree_roster(output_dir)
    archive = output_dir / "onnx.tar.gz"
    if not archive.is_file() or archive.is_symlink():
        raise ValueError("MiniLM archive is missing or unsafe")
    if _sha256_file(archive) != expected_archive_sha256:
        raise ValueError("MiniLM archive SHA-256 mismatch")
    return stored


def prepare_artifact(
    output_dir: Path,
    *,
    archive_path: Path | None = None,
    allow_network: bool = False,
    source_url: str = MEMPALACE_MINILM_ARCHIVE_URL,
    expected_archive_sha256: str = MEMPALACE_MINILM_ARCHIVE_SHA256,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        return verify_prepared_artifact(
            output_dir, expected_archive_sha256=expected_archive_sha256
        )
    if archive_path is None and not allow_network:
        raise ValueError("provide a local MiniLM archive or explicitly allow network acquisition")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        staged_archive = staging / "onnx.tar.gz"
        if archive_path is not None:
            archive_path = archive_path.resolve()
            if not archive_path.is_file() or archive_path.is_symlink():
                raise ValueError("MiniLM source archive must be a regular non-symlink file")
            with archive_path.open("rb") as source, staged_archive.open(
                "xb", buffering=0
            ) as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
                os.fsync(destination.fileno())
        else:
            _download(staged_archive, url=source_url)
        if _sha256_file(staged_archive) != expected_archive_sha256:
            raise ValueError("MiniLM source archive SHA-256 mismatch")
        _extract_exact_archive(staged_archive, staging)
        files = _file_manifest(staging)
        receipt = _receipt(files=files, archive_sha256=expected_archive_sha256)
        receipt_path = staging / RECEIPT_NAME
        with receipt_path.open("xb", buffering=0) as handle:
            handle.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
            os.fsync(handle.fileno())
        _fsync_directory(staging / "onnx")
        _fsync_directory(staging)
        os.replace(staging, output_dir)
        _fsync_directory(output_dir.parent)
        return verify_prepared_artifact(
            output_dir, expected_archive_sha256=expected_archive_sha256
        )
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify_only:
            if args.archive is not None or args.allow_network:
                parser.error("--verify-only cannot acquire an archive")
            receipt = verify_prepared_artifact(args.output_dir)
        else:
            receipt = prepare_artifact(
                args.output_dir,
                archive_path=args.archive,
                allow_network=args.allow_network,
            )
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f"{receipt['status']} root={receipt['artifact_root_sha256']} "
        f"receipt={receipt['receipt_sha256']} output={args.output_dir.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
