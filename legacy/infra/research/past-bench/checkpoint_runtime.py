#!/usr/bin/env python3
"""Atomic episode-boundary checkpoints for the contained PAST-Bench lane.

This module deliberately knows nothing about model calls or benchmark scoring.
The patched PAST runner owns episode semantics and calls :class:`CheckpointStore`
only after an episode, its optional reflection, and its persistence anchor have
all completed.  A checkpoint is a complete immutable snapshot of the trace root
plus a small state record bound to the exact execution identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
STAGES = {
    "shared-cold-complete",
    "episode-complete",
    "variant-complete",
    "run-complete",
}
REQUIRED_IDENTITY_FIELDS = {
    "source_revision",
    "source_receipt_sha256",
    "runtime_receipt_sha256",
    "image_id",
    "sealed_sbom_sha256",
    "model_receipt_sha256",
    "experiment_sha256",
    "argv",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")


class PastCheckpointError(ValueError):
    """Raised when checkpoint identity, durability, or contents are invalid."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _root(value: Any) -> str:
    return _sha256_bytes(_canonical(value))


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_regular(path: Path, *, owner: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PastCheckpointError(f"{owner} is not a readable regular file: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise PastCheckpointError(f"{owner} is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise PastCheckpointError(f"{owner} changed while it was read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _validate_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(identity)
    if set(normalized) != REQUIRED_IDENTITY_FIELDS:
        raise PastCheckpointError("checkpoint identity has an unexpected field roster")
    for field in REQUIRED_IDENTITY_FIELDS - {"argv"}:
        value = normalized[field]
        if not isinstance(value, str) or not value:
            raise PastCheckpointError(f"checkpoint identity {field} is invalid")
    if not GIT_SHA_RE.fullmatch(normalized["source_revision"]):
        raise PastCheckpointError("checkpoint identity source_revision is malformed")
    for field in {
        "source_receipt_sha256",
        "runtime_receipt_sha256",
        "sealed_sbom_sha256",
        "model_receipt_sha256",
        "experiment_sha256",
    }:
        if not SHA256_RE.fullmatch(normalized[field]):
            raise PastCheckpointError(f"checkpoint identity {field} is malformed")
    if not IMAGE_ID_RE.fullmatch(normalized["image_id"]):
        raise PastCheckpointError("checkpoint identity image_id is malformed")
    argv = normalized["argv"]
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        raise PastCheckpointError("checkpoint identity argv must be a nonempty string list")
    return normalized


def load_execution_identity(path: Path) -> dict[str, Any]:
    """Load one exact checkpoint identity without following a symlink."""

    try:
        value = json.loads(_read_regular(path, owner="checkpoint identity"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PastCheckpointError(f"checkpoint identity is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise PastCheckpointError("checkpoint identity must be a JSON object")
    return _validate_identity(value)


def _safe_tree_manifest(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir() or root.is_symlink():
        raise PastCheckpointError(f"checkpoint payload is not a regular directory: {root}")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        pure = PurePosixPath(relative.as_posix())
        if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
            raise PastCheckpointError(f"unsafe checkpoint payload path: {relative}")
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise PastCheckpointError(f"checkpoint payload contains a symlink: {relative}")
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISDIR(info.st_mode):
            rows.append({"path": pure.as_posix(), "kind": "directory", "mode": mode})
            continue
        if not stat.S_ISREG(info.st_mode):
            raise PastCheckpointError(f"checkpoint payload contains a special file: {relative}")
        content = _read_regular(path, owner="checkpoint payload file")
        rows.append(
            {
                "path": pure.as_posix(),
                "kind": "file",
                "mode": mode,
                "size": len(content),
                "sha256": _sha256_bytes(content),
            }
        )
    return rows


def _write_json(path: Path, value: Any) -> None:
    payload = _canonical(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _copy_tree(source: Path, destination: Path) -> None:
    _safe_tree_manifest(source)
    shutil.copytree(source, destination, symlinks=False)
    for path in sorted(destination.rglob("*"), reverse=True):
        if path.is_file():
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        elif path.is_dir():
            _fsync_dir(path)
    _fsync_dir(destination)


class CheckpointStore:
    """Write and restore immutable, identity-bound checkpoint generations."""

    def __init__(
        self,
        *,
        checkpoint_root: Path,
        trace_root: Path,
        identity: Mapping[str, Any],
        marker: Path | None = None,
        retain_generations: int = 2,
    ) -> None:
        if checkpoint_root.exists() and checkpoint_root.is_symlink():
            raise PastCheckpointError("checkpoint root cannot be a symlink")
        if trace_root.exists() and trace_root.is_symlink():
            raise PastCheckpointError("trace root cannot be a symlink")
        self.checkpoint_root = checkpoint_root.resolve()
        self.trace_root = trace_root.resolve()
        if (
            self.checkpoint_root == self.trace_root
            or self.checkpoint_root in self.trace_root.parents
        ):
            raise PastCheckpointError("checkpoint root cannot contain the trace root")
        if self.trace_root in self.checkpoint_root.parents:
            raise PastCheckpointError("checkpoint root cannot be inside the trace root")
        if retain_generations < 2:
            raise PastCheckpointError("at least two checkpoint generations must be retained")
        self.identity = _validate_identity(identity)
        self.identity_sha256 = _root(self.identity)
        self.marker = marker.resolve() if marker is not None else None
        self.retain_generations = retain_generations
        self.checkpoint_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        _fsync_dir(self.checkpoint_root.parent)

    def _generation_dirs(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.checkpoint_root.iterdir()
                if path.is_dir() and not path.is_symlink() and path.name.startswith("generation-")
            ),
            key=lambda path: path.name,
        )

    def _next_index(self) -> int:
        indexes: list[int] = []
        for path in self._generation_dirs():
            try:
                indexes.append(int(path.name.split("-", 2)[1]))
            except (IndexError, ValueError) as exc:
                raise PastCheckpointError(f"malformed checkpoint generation: {path.name}") from exc
        return max(indexes, default=0) + 1

    def commit(
        self,
        *,
        stage: str,
        variant: str | None,
        completed_episode: int,
        episode_results: Sequence[Mapping[str, Any]],
        extra_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if stage not in STAGES:
            raise PastCheckpointError(f"unsupported checkpoint stage: {stage}")
        if not isinstance(completed_episode, int) or completed_episode < 0:
            raise PastCheckpointError("completed_episode must be a nonnegative integer")
        if variant is not None and (not isinstance(variant, str) or not variant):
            raise PastCheckpointError("checkpoint variant is invalid")
        if not self.trace_root.is_dir() or self.trace_root.is_symlink():
            raise PastCheckpointError("trace root must exist before checkpoint commit")

        generation_index = self._next_index()
        temporary = Path(tempfile.mkdtemp(prefix=".checkpoint-staging-", dir=self.checkpoint_root))
        try:
            payload = temporary / "payload"
            _copy_tree(self.trace_root, payload)
            manifest = _safe_tree_manifest(payload)
            state = {
                "schema_version": SCHEMA_VERSION,
                "stage": stage,
                "variant": variant,
                "completed_episode": completed_episode,
                "episode_results": [dict(item) for item in episode_results],
                "extra_state": dict(extra_state or {}),
            }
            _write_json(temporary / "state.json", state)
            _write_json(temporary / "payload-manifest.json", manifest)
            unsigned = {
                "schema_version": SCHEMA_VERSION,
                "generation": generation_index,
                "identity": self.identity,
                "identity_sha256": self.identity_sha256,
                "state_sha256": _root(state),
                "payload_file_count": sum(row["kind"] == "file" for row in manifest),
                "payload_manifest_sha256": _root(manifest),
            }
            receipt = {**unsigned, "receipt_sha256": _root(unsigned)}
            _write_json(temporary / "receipt.json", receipt)
            _fsync_dir(temporary)

            final = self.checkpoint_root / (
                f"generation-{generation_index:08d}-{receipt['receipt_sha256'][:12]}"
            )
            if final.exists():
                raise PastCheckpointError(f"checkpoint generation already exists: {final}")
            os.rename(temporary, final)
            _fsync_dir(self.checkpoint_root)

            pointer_temp = self.checkpoint_root / f".LATEST.{os.getpid()}"
            _write_json(
                pointer_temp,
                {"generation": final.name, "receipt_sha256": receipt["receipt_sha256"]},
            )
            os.replace(pointer_temp, self.checkpoint_root / "LATEST")
            _fsync_dir(self.checkpoint_root)

            generations = self._generation_dirs()
            for stale in generations[: -self.retain_generations]:
                shutil.rmtree(stale)
            _fsync_dir(self.checkpoint_root)

            if self.marker is not None:
                self.marker.parent.mkdir(parents=True, exist_ok=True)
                marker_temp = self.marker.with_name(f".{self.marker.name}.{os.getpid()}")
                _write_json(
                    marker_temp,
                    {"receipt_sha256": receipt["receipt_sha256"], "generation": final.name},
                )
                os.replace(marker_temp, self.marker)
                _fsync_dir(self.marker.parent)
            return receipt
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    def _load_latest(self) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        pointer_path = self.checkpoint_root / "LATEST"
        try:
            pointer = json.loads(_read_regular(pointer_path, owner="checkpoint pointer"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise PastCheckpointError(f"checkpoint pointer is invalid: {exc}") from exc
        if not isinstance(pointer, dict) or set(pointer) != {"generation", "receipt_sha256"}:
            raise PastCheckpointError("checkpoint pointer field roster is invalid")
        generation_name = pointer["generation"]
        if (
            not isinstance(generation_name, str)
            or "/" in generation_name
            or not generation_name.startswith("generation-")
        ):
            raise PastCheckpointError("checkpoint generation pointer is invalid")
        generation = self.checkpoint_root / generation_name
        if not generation.is_dir() or generation.is_symlink():
            raise PastCheckpointError("checkpoint generation is absent or not a regular directory")
        try:
            receipt = json.loads(
                _read_regular(generation / "receipt.json", owner="checkpoint receipt")
            )
            state = json.loads(_read_regular(generation / "state.json", owner="checkpoint state"))
            manifest = json.loads(
                _read_regular(generation / "payload-manifest.json", owner="checkpoint manifest")
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise PastCheckpointError(f"checkpoint metadata is invalid: {exc}") from exc
        if (
            not isinstance(receipt, dict)
            or not isinstance(state, dict)
            or not isinstance(manifest, list)
        ):
            raise PastCheckpointError("checkpoint metadata has invalid types")
        unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if receipt.get("receipt_sha256") != _root(unsigned):
            raise PastCheckpointError("checkpoint receipt digest is invalid")
        if pointer["receipt_sha256"] != receipt["receipt_sha256"]:
            raise PastCheckpointError("checkpoint pointer and receipt differ")
        if (
            receipt.get("identity") != self.identity
            or receipt.get("identity_sha256") != self.identity_sha256
        ):
            raise PastCheckpointError("checkpoint execution identity drifted")
        if receipt.get("state_sha256") != _root(state):
            raise PastCheckpointError("checkpoint state digest is invalid")
        if receipt.get("payload_manifest_sha256") != _root(manifest):
            raise PastCheckpointError("checkpoint manifest digest is invalid")
        actual_manifest = _safe_tree_manifest(generation / "payload")
        if manifest != actual_manifest:
            raise PastCheckpointError("checkpoint payload differs from its manifest")
        if receipt.get("payload_file_count") != sum(row.get("kind") == "file" for row in manifest):
            raise PastCheckpointError("checkpoint payload file count is invalid")
        return generation, receipt, state

    def restore_latest(self) -> dict[str, Any]:
        generation, receipt, state = self._load_latest()
        if self.trace_root.exists() and self.trace_root.is_symlink():
            raise PastCheckpointError("resume trace root cannot be a symlink")
        if self.trace_root.exists() and any(self.trace_root.iterdir()):
            if _safe_tree_manifest(self.trace_root) != _safe_tree_manifest(generation / "payload"):
                raise PastCheckpointError(
                    "existing resume trace root differs from the latest checkpoint"
                )
            return {
                "receipt": receipt,
                "state": state,
                "generation": generation.name,
            }
        self.trace_root.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(
            tempfile.mkdtemp(prefix=f".{self.trace_root.name}.restore-", dir=self.trace_root.parent)
        )
        temporary.rmdir()
        try:
            _copy_tree(generation / "payload", temporary)
            if self.trace_root.exists():
                self.trace_root.rmdir()
            os.rename(temporary, self.trace_root)
            _fsync_dir(self.trace_root.parent)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return {
            "receipt": receipt,
            "state": state,
            "generation": generation.name,
        }


__all__ = ["CheckpointStore", "PastCheckpointError", "load_execution_identity"]
