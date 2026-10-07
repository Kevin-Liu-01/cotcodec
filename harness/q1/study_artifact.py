"""Hash-bound hand-off of Q1 inputs between lane jobs (one study artifact per job).

The lane mounts exactly one read-only, SHA-256-checked file per job at
``/inputs/study-artifact.json`` (``study_artifact`` in the job manifest, at
most 512 MiB; ``docs/operations.md``). Q1 jobs need more than one input tree:
the unmodified upstream clones the fidelity gates import (KernelGYM, which has
no licence and is never committed; KernelBench-Verified) and the corpus a
previous job built (substrates, specializations, selected mutants, controls).
This module packs such trees into one JSON document and unpacks it inside the
job after checking every hash.

Document (``q1-study-artifact/1``)::

    {"schema": ..., "repo_revision": <40-hex>, "trees": {name: tree}, "manifest_sha256": ...}
    tree = {"kind": "git" | "dir", "source": str, "revision": <40-hex> | null,
            "licence": str, "files": [{"path", "mode", "size", "sha256",
            "git_blob" (git trees), "b64"}], "skipped": [...], "tree_sha256": ...}

``tree_sha256`` is SHA-256 over ``path NUL sha256 LF`` of every file in path
order; ``manifest_sha256`` is SHA-256 of the canonical JSON of the document
with every ``b64`` removed. A git tree is read from the object store at the
pinned revision (``git ls-tree``/``git cat-file``), never from a working tree,
so local edits cannot leak in; each file also records its git blob id, which
must match the blob that ``git ls-tree`` names. Unpacking checks the file's
SHA-256 (the lane's), then the manifest, then every tree and file hash, and
writes files read-only; a git tree also gets a ``REVISION`` file (the marker
the fidelity loaders read for exported trees), listed as an addition.

Pure Python; no torch.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "q1-study-artifact/1"
MAX_BYTES = 512 * 1024**2
REVISION_MARKER = "REVISION"
_SKIP_DIR_NAMES = {"__pycache__", ".git", ".ruff_cache", ".pytest_cache"}


class ArtifactError(ValueError):
    """The artifact is malformed or a hash does not match."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # noqa: S324 - git id


def tree_sha256(files: Iterable[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(files, key=lambda f: f["path"]):
        digest.update(f"{entry['path']}\0{entry['sha256']}\n".encode())
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def manifest_sha256(document: Mapping[str, Any]) -> str:
    stripped = {key: value for key, value in document.items() if key != "manifest_sha256"}
    stripped["trees"] = {
        name: {
            **tree,
            "files": [{k: v for k, v in f.items() if k != "b64"} for f in tree["files"]],
        }
        for name, tree in document["trees"].items()
    }
    return sha256_bytes(_canonical(stripped))


def _safe_relpath(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.is_absolute() or not pure.parts or any(p in {"", ".", ".."} for p in pure.parts):
        raise ArtifactError(f"unsafe path in artifact: {path!r}")
    return pure.as_posix()


def _entry(path: str, data: bytes, mode: int, *, git: bool) -> dict[str, Any]:
    entry = {
        "path": _safe_relpath(path),
        "mode": 0o755 if mode & 0o111 else 0o644,
        "size": len(data),
        "sha256": sha256_bytes(data),
        "b64": base64.b64encode(data).decode("ascii"),
    }
    if git:
        entry["git_blob"] = git_blob_id(data)
    return entry


def git_tree(clone: Path, revision: str, *, source: str, licence: str) -> dict[str, Any]:
    """Every regular file of ``revision`` in ``clone``, read from the object store."""
    listing = subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(clone), "ls-tree", "-r", "-z", revision],
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    files: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for record in filter(None, listing):
        meta, _, raw_path = record.partition(b"\t")
        mode_text, kind, blob = meta.decode().split()
        path = raw_path.decode("utf-8")
        if kind != "blob" or mode_text not in {"100644", "100755"}:
            skipped.append({"path": path, "mode": mode_text, "type": kind})
            continue
        data = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(clone), "cat-file", "blob", blob],
            check=True,
            capture_output=True,
        ).stdout
        entry = _entry(path, data, int(mode_text, 8), git=True)
        if entry["git_blob"] != blob:
            raise ArtifactError(f"{path}: blob {entry['git_blob']} != tree entry {blob}")
        files.append(entry)
    resolved = subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(clone), "rev-parse", f"{revision}^{{commit}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    files.sort(key=lambda f: f["path"])
    return {
        "kind": "git",
        "source": source,
        "revision": resolved,
        "licence": licence,
        "files": files,
        "skipped": skipped,
        "tree_sha256": tree_sha256(files),
    }


def dir_tree(root: Path, *, source: str, licence: str) -> dict[str, Any]:
    """Every regular file under ``root`` (no symlinks; caches skipped and listed)."""
    root = Path(root)
    files: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for current, dirnames, filenames in os.walk(root):
        keep = []
        for name in sorted(dirnames):
            rel = (Path(current) / name).relative_to(root).as_posix()
            if name in _SKIP_DIR_NAMES or (Path(current) / name).is_symlink():
                skipped.append({"path": rel, "type": "directory"})
            else:
                keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or name.endswith((".pyc", ".pyo")):
                skipped.append({"path": rel, "type": "not-regular-or-bytecode"})
                continue
            files.append(_entry(rel, path.read_bytes(), info.st_mode, git=False))
    files.sort(key=lambda f: f["path"])
    return {
        "kind": "dir",
        "source": source,
        "revision": None,
        "licence": licence,
        "files": files,
        "skipped": skipped,
        "tree_sha256": tree_sha256(files),
    }


def build(trees: Mapping[str, Mapping[str, Any]], *, repo_revision: str) -> dict[str, Any]:
    document = {"schema": SCHEMA, "repo_revision": repo_revision, "trees": dict(trees)}
    document["manifest_sha256"] = manifest_sha256(document)
    return document


def write(document: Mapping[str, Any], out: Path) -> dict[str, Any]:
    data = _canonical(document)
    if len(data) > MAX_BYTES:
        raise ArtifactError(f"artifact is {len(data)} bytes, above the lane's {MAX_BYTES}")
    out = Path(out)
    out.write_bytes(data)
    return {
        "path": str(out),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "manifest_sha256": document["manifest_sha256"],
        "trees": {
            name: {
                "files": len(tree["files"]),
                "tree_sha256": tree["tree_sha256"],
                "revision": tree.get("revision"),
            }
            for name, tree in document["trees"].items()
        },
    }


def load(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Read and verify an artifact: file SHA-256, schema, manifest and every hash."""
    data = Path(path).read_bytes()
    if sha256_bytes(data) != expected_sha256:
        raise ArtifactError("study artifact SHA-256 differs from the expected value")
    document = json.loads(data)
    if document.get("schema") != SCHEMA:
        raise ArtifactError(f"unknown artifact schema {document.get('schema')!r}")
    if manifest_sha256(document) != document.get("manifest_sha256"):
        raise ArtifactError("artifact manifest hash does not match its contents")
    for name, tree in document["trees"].items():
        for entry in tree["files"]:
            content = base64.b64decode(entry["b64"])
            if sha256_bytes(content) != entry["sha256"] or len(content) != entry["size"]:
                raise ArtifactError(f"{name}/{entry['path']}: content hash mismatch")
            if "git_blob" in entry and git_blob_id(content) != entry["git_blob"]:
                raise ArtifactError(f"{name}/{entry['path']}: git blob mismatch")
        if tree_sha256(tree["files"]) != tree["tree_sha256"]:
            raise ArtifactError(f"{name}: tree hash mismatch")
    return document


def unpack(
    document: Mapping[str, Any], out_root: Path, *, names: Iterable[str] | None = None
) -> dict[str, Any]:
    """Write verified trees under ``out_root/<name>/`` read-only; return a receipt."""
    out_root = Path(out_root)
    receipt: dict[str, Any] = {"manifest_sha256": document["manifest_sha256"], "trees": {}}
    wanted = list(document["trees"]) if names is None else list(names)
    for name in wanted:
        tree = document["trees"][name]
        target = out_root / _safe_relpath(name)
        if target.exists():
            raise ArtifactError(f"{target} exists; refusing to overwrite")
        target.mkdir(parents=True)
        for entry in tree["files"]:
            path = target / _safe_relpath(entry["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(entry["b64"]))
            path.chmod(0o555 if entry["mode"] & 0o111 else 0o444)
        added = []
        if tree["kind"] == "git" and tree.get("revision"):
            marker = target / REVISION_MARKER
            if not marker.exists():
                marker.write_text(tree["revision"] + "\n", encoding="utf-8")
                marker.chmod(0o444)
                added.append(REVISION_MARKER)
        for directory in sorted({p for p in target.rglob("*") if p.is_dir()}, reverse=True):
            directory.chmod(0o555)
        target.chmod(0o555)
        receipt["trees"][name] = {
            "path": str(target),
            "files": len(tree["files"]),
            "tree_sha256": tree["tree_sha256"],
            "revision": tree.get("revision"),
            "source": tree["source"],
            "licence": tree["licence"],
            "added": added,
        }
    return receipt


__all__ = [
    "ArtifactError",
    "MAX_BYTES",
    "SCHEMA",
    "build",
    "dir_tree",
    "git_blob_id",
    "git_tree",
    "load",
    "manifest_sha256",
    "tree_sha256",
    "unpack",
    "write",
]
