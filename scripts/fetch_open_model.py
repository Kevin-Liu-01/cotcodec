#!/usr/bin/env python3
"""Fetch pinned open-model artifacts and write reproducibility receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = PROJECT_ROOT / "models" / "registry.yaml"
DEFAULT_MODEL_ROOT = Path(
    os.environ.get("COTCODEC_MODEL_ROOT", PROJECT_ROOT / "data" / "models")
)
DEFAULT_RECEIPT_ROOT = PROJECT_ROOT / "data" / "model-receipts"
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ModelRegistryError(ValueError):
    """Raised when a model registry or receipt violates the contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ModelRegistryError("registry must be a schema_version: 1 mapping")
    models = payload.get("models")
    if not isinstance(models, dict) or not models:
        raise ModelRegistryError("registry.models must be a non-empty mapping")

    for model_id, entry in models.items():
        if not isinstance(model_id, str) or not MODEL_ID_RE.fullmatch(model_id):
            raise ModelRegistryError(f"invalid model id: {model_id!r}")
        if not isinstance(entry, dict):
            raise ModelRegistryError(f"{model_id}: entry must be a mapping")
        validate_entry(model_id, entry)
    return payload


def validate_entry(model_id: str, entry: dict[str, Any]) -> None:
    backend = entry.get("backend")
    if backend not in {"huggingface", "ollama"}:
        raise ModelRegistryError(f"{model_id}: unsupported backend {backend!r}")
    for field in (
        "runtime",
        "architecture_family",
        "license",
        "access",
        "source_url",
    ):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ModelRegistryError(f"{model_id}: {field} must be a non-empty string")
    if not isinstance(entry.get("trust_remote_code"), bool):
        raise ModelRegistryError(f"{model_id}: trust_remote_code must be boolean")
    if not isinstance(entry.get("publication_eligible"), bool):
        raise ModelRegistryError(f"{model_id}: publication_eligible must be boolean")
    if backend == "huggingface":
        if not isinstance(entry.get("repo_id"), str) or "/" not in entry["repo_id"]:
            raise ModelRegistryError(f"{model_id}: invalid Hugging Face repo_id")
        revision = entry.get("revision")
        if not isinstance(revision, str) or not COMMIT_RE.fullmatch(revision):
            raise ModelRegistryError(f"{model_id}: revision must be a 40-char commit")
        for field in ("metadata_files", "required_files"):
            values = entry.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise ModelRegistryError(f"{model_id}: {field} must be a string list")
    else:
        if not isinstance(entry.get("model_ref"), str) or ":" not in entry["model_ref"]:
            raise ModelRegistryError(f"{model_id}: Ollama model_ref must include a tag")
        if entry["publication_eligible"]:
            raise ModelRegistryError(f"{model_id}: mutable Ollama tags cannot be publication-ready")

    if entry["publication_eligible"]:
        if entry["trust_remote_code"]:
            raise ModelRegistryError(
                f"{model_id}: unreviewed remote code blocks publication eligibility"
            )
        if entry["license"].startswith(("unresolved", "upstream-dependent")):
            raise ModelRegistryError(
                f"{model_id}: unresolved license blocks publication eligibility"
            )


def snapshot_files(snapshot: Path) -> list[dict[str, Any]]:
    if not snapshot.is_dir():
        raise ModelRegistryError(f"snapshot does not exist: {snapshot}")
    files: list[dict[str, Any]] = []
    for path in sorted(snapshot.rglob("*")):
        relative = path.relative_to(snapshot)
        if not path.is_file() or relative.parts[:2] == (".cache", "huggingface"):
            continue
        files.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return files


def artifact_root(files: list[dict[str, Any]]) -> str:
    encoded = json.dumps(files, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def receipt_path(receipt_root: Path, model_id: str) -> Path:
    return receipt_root / f"{model_id}.json"


def fetch_huggingface(
    model_id: str,
    entry: dict[str, Any],
    registry_path: Path,
    model_root: Path,
    receipt_root: Path,
    metadata_only: bool,
) -> dict[str, Any]:
    from huggingface_hub import HfApi, snapshot_download

    revision = entry["revision"]
    info = HfApi().model_info(entry["repo_id"], revision=revision)
    if info.sha != revision:
        raise ModelRegistryError(
            f"{model_id}: Hub resolved {info.sha!r}, expected immutable {revision}"
        )

    target = model_root / model_id
    target.mkdir(parents=True, exist_ok=True)
    allow_patterns = entry["metadata_files"] if metadata_only else None
    snapshot_download(
        repo_id=entry["repo_id"],
        revision=revision,
        local_dir=target,
        allow_patterns=allow_patterns,
    )
    files = snapshot_files(target)
    found = {item["path"] for item in files}
    expected = entry["metadata_files"] if metadata_only else entry["required_files"]
    missing = sorted(set(expected) - found)
    if missing:
        raise ModelRegistryError(f"{model_id}: downloaded snapshot misses {missing}")

    receipt = {
        "schema_version": 1,
        "model_id": model_id,
        "backend": "huggingface",
        "repo_id": entry["repo_id"],
        "revision": revision,
        "mode": "metadata" if metadata_only else "full",
        "registry_sha256": sha256_file(registry_path),
        "publication_eligible": entry["publication_eligible"] and not metadata_only,
        "trust_remote_code": entry["trust_remote_code"],
        "files": files,
        "total_bytes": sum(item["bytes"] for item in files),
        "artifact_root_sha256": artifact_root(files),
    }
    atomic_json(receipt_path(receipt_root, model_id), receipt)
    return receipt


def ollama_modelfile(model_ref: str) -> str:
    if shutil.which("ollama") is None:
        raise ModelRegistryError("ollama executable is not installed")
    result = subprocess.run(
        ["ollama", "show", model_ref, "--modelfile"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def fetch_ollama(
    model_id: str,
    entry: dict[str, Any],
    registry_path: Path,
    receipt_root: Path,
) -> dict[str, Any]:
    if shutil.which("ollama") is None:
        raise ModelRegistryError("ollama executable is not installed")
    subprocess.run(["ollama", "pull", entry["model_ref"]], check=True)
    modelfile = ollama_modelfile(entry["model_ref"])
    receipt = {
        "schema_version": 1,
        "model_id": model_id,
        "backend": "ollama",
        "model_ref": entry["model_ref"],
        "mode": "mutable-smoke-alias",
        "registry_sha256": sha256_file(registry_path),
        "publication_eligible": False,
        "modelfile_sha256": hashlib.sha256(modelfile.encode()).hexdigest(),
    }
    atomic_json(receipt_path(receipt_root, model_id), receipt)
    return receipt


def verify_receipt(
    model_id: str,
    entry: dict[str, Any],
    model_root: Path,
    receipt_root: Path,
) -> dict[str, Any]:
    path = receipt_path(receipt_root, model_id)
    if not path.is_file():
        raise ModelRegistryError(f"receipt does not exist: {path}")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("model_id") != model_id or receipt.get("backend") != entry["backend"]:
        raise ModelRegistryError(f"{model_id}: receipt identity does not match registry")

    if entry["backend"] == "huggingface":
        if receipt.get("revision") != entry["revision"]:
            raise ModelRegistryError(f"{model_id}: receipt revision does not match registry")
        actual = snapshot_files(model_root / model_id)
        if actual != receipt.get("files"):
            raise ModelRegistryError(f"{model_id}: local files no longer match receipt")
        if artifact_root(actual) != receipt.get("artifact_root_sha256"):
            raise ModelRegistryError(f"{model_id}: artifact root mismatch")
    else:
        modelfile = ollama_modelfile(entry["model_ref"])
        actual_hash = hashlib.sha256(modelfile.encode()).hexdigest()
        if actual_hash != receipt.get("modelfile_sha256"):
            raise ModelRegistryError(f"{model_id}: Ollama alias content changed")
    return receipt


def print_receipt(receipt: dict[str, Any]) -> None:
    summary = {
        key: receipt[key]
        for key in (
            "model_id",
            "backend",
            "mode",
            "revision",
            "total_bytes",
            "artifact_root_sha256",
            "publication_eligible",
        )
        if key in receipt
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("model_id")
    fetch.add_argument("--metadata-only", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("model_id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    registry_path = args.registry.resolve()
    registry = load_registry(registry_path)
    models = registry["models"]
    if args.command == "list":
        for model_id, entry in models.items():
            print(
                f"{model_id:24} {entry['backend']:12} "
                f"{entry['architecture_family']:24} publication={entry['publication_eligible']}"
            )
        return 0

    if args.model_id not in models:
        raise ModelRegistryError(f"unknown model id: {args.model_id}")
    entry = models[args.model_id]
    if args.command == "fetch":
        if entry["backend"] == "huggingface":
            receipt = fetch_huggingface(
                args.model_id,
                entry,
                registry_path,
                args.model_root.resolve(),
                args.receipt_root.resolve(),
                args.metadata_only,
            )
        else:
            if args.metadata_only:
                raise ModelRegistryError("--metadata-only is only valid for Hugging Face")
            receipt = fetch_ollama(
                args.model_id, entry, registry_path, args.receipt_root.resolve()
            )
    else:
        receipt = verify_receipt(
            args.model_id,
            entry,
            args.model_root.resolve(),
            args.receipt_root.resolve(),
        )
    print_receipt(receipt)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ModelRegistryError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
