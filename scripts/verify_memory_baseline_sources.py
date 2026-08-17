#!/usr/bin/env python3
"""Verify exact native memory-system checkouts and emit a sealed source receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate  # noqa: E402

DEFAULT_CONTRACT = PROJECT_ROOT / "experiments" / "memory" / "stage2-oss-baselines.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "memory-baselines" / "source-preflight.json"


class BaselineSourceError(ValueError):
    """Raised when a native baseline cannot be bound to its registered source."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(checkout: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BaselineSourceError(f"git {' '.join(args)} failed for {checkout}: {detail}")
    return result.stdout.strip()


def _git_archive_sha256(checkout: Path, revision: str) -> str:
    process = subprocess.Popen(
        ["git", "-C", str(checkout), "archive", "--format=tar", revision],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:
        raise BaselineSourceError("failed to open git archive pipes")
    digest = hashlib.sha256()
    for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
        digest.update(chunk)
    stderr = process.stderr.read().decode(errors="replace").strip()
    returncode = process.wait()
    if returncode:
        raise BaselineSourceError(f"git archive failed for {checkout}: {stderr}")
    return digest.hexdigest()


def _normalize_repo_url(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def _implementation_repository(source: dict[str, Any], role: str) -> dict[str, Any]:
    matches = [repo for repo in source.get("repositories", []) if repo.get("role") == role]
    if len(matches) != 1:
        raise BaselineSourceError(f"source must have exactly one repository with role {role!r}")
    return matches[0]


def load_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if not isinstance(contract, dict) or contract.get("schema_version") != 1:
        raise BaselineSourceError("baseline contract must be a schema_version: 1 mapping")
    systems = contract.get("systems")
    if not isinstance(systems, dict) or not systems:
        raise BaselineSourceError("baseline contract systems must be a non-empty mapping")
    protocol = contract.get("protocol")
    if not isinstance(protocol, dict):
        raise BaselineSourceError("baseline contract protocol must be a mapping")
    native_fields = protocol.get("native_request_fields")
    if native_fields != [
        "session_scope",
        "ordered_prefix_events",
        "query",
        "budget",
    ]:
        raise BaselineSourceError(
            "native request fields must stay task-blind and exclude benchmark stratum"
        )
    status = contract.get("implementation_status")
    if not isinstance(status, dict):
        raise BaselineSourceError("baseline contract implementation_status is required")
    if status.get("scientific_result") is not False:
        raise BaselineSourceError(
            "ephemeral native mechanism slices cannot be labeled a scientific result"
        )
    transport_status = status.get("transport_status")
    if transport_status != {
        "memory_system_v1_persistent_reference_process": "implemented",
        "memory_lifecycle_v1_reference_contract": "implemented",
        "contained_cpu_reference_matrix": "pass-development-evidence",
        "cross_runtime_semantic_equivalence": "pass-development-evidence",
        "native_systems_migrated": False,
        "backend_state_verified": False,
    }:
        raise BaselineSourceError(
            "transport status must distinguish the reference doctor from native persistence"
        )
    required_blockers = {
        "native_systems_not_migrated_to_memory_lifecycle_v1",
        "backend_verified_restart_persistence",
        "backend_verified_purge_and_residue_inspection",
        "matched_full_native_construction_models_and_costs",
        "frozen_four_system_task_bundle_and_actor_outcomes",
    }
    if set(status.get("blockers", [])) != required_blockers:
        raise BaselineSourceError("native baseline implementation blockers drifted")
    lifecycle_evidence = status.get("reference_lifecycle_evidence")
    expected_lifecycle_evidence = {
        "protocol": "memory-lifecycle-v1",
        "host_manifest_sha256": (
            "92a062233cc173a16a022e8c2d99edccec8db90272a10b53a40f8fb03a8a0d90"
        ),
        "container_manifest_sha256": (
            "2ac7a67c05f4b88540d86361413201438d996ec174f22c4c98bf0ffd947624ac"
        ),
        "comparison_sha256": ("906c900abaa5a5814cacc104ed582c90f24784f98ac3325ed6490e3837799d61"),
        "cases": 192,
        "capacity_cells": [2, 4, 8],
        "task_families": [
            "active_archive",
            "update_delete",
            "consolidation",
            "feedback",
        ],
        "container_image_id": (
            "sha256:359a1766c820f21c020a4130a85bdee5850e2f0410b20dbfdf283e90f310f9a5"
        ),
        "network_mode": "none",
        "publication_attested": False,
        "evidence_role": "reference-transport-and-mechanism-determinism-only",
    }
    if lifecycle_evidence != expected_lifecycle_evidence:
        raise BaselineSourceError("reference lifecycle evidence drifted")
    lifecycle_protocol = contract.get("lifecycle_protocol")
    if not isinstance(lifecycle_protocol, dict):
        raise BaselineSourceError("memory-lifecycle-v1 contract is required")
    if lifecycle_protocol.get("id") != "memory-lifecycle-v1":
        raise BaselineSourceError("lifecycle protocol ID drifted")
    if lifecycle_protocol.get("fail_closed_on_missing_capability") is not True:
        raise BaselineSourceError("lifecycle capabilities must fail closed")
    if lifecycle_protocol.get("branch_isolation_required") is not True:
        raise BaselineSourceError("lifecycle branch isolation is required")
    if lifecycle_protocol.get("deterministic_restart_required_for_deterministic_arms") is not True:
        raise BaselineSourceError("deterministic lifecycle arms require restart proof")
    ledger = load_and_validate(ledger_path)
    seen_revisions: set[str] = set()
    for system_id, system in systems.items():
        if not isinstance(system, dict):
            raise BaselineSourceError(f"{system_id}: system contract must be a mapping")
        source_id = system.get("source_id")
        if source_id not in ledger["sources"]:
            raise BaselineSourceError(f"{system_id}: unknown source_id {source_id!r}")
        role = system.get("repository_role")
        registered = _implementation_repository(ledger["sources"][source_id], role)
        for field in ("revision", "license"):
            if system.get(field) != registered.get(field):
                raise BaselineSourceError(f"{system_id}: {field} differs from the source ledger")
        revision = system["revision"]
        if revision in seen_revisions:
            raise BaselineSourceError(f"{system_id}: duplicate implementation revision")
        seen_revisions.add(revision)
        checkout = system.get("checkout")
        if not isinstance(checkout, str) or not checkout.startswith("raw/baselines/"):
            raise BaselineSourceError(f"{system_id}: checkout must be below raw/baselines")
        for field in (
            "package",
            "package_version",
            "python",
            "package_file",
            "public_api_file",
        ):
            if not isinstance(system.get(field), str) or not system[field]:
                raise BaselineSourceError(f"{system_id}: {field} must be non-empty")
        symbols = system.get("public_api_symbols")
        if (
            not isinstance(symbols, list)
            or not symbols
            or not all(isinstance(symbol, str) and symbol for symbol in symbols)
        ):
            raise BaselineSourceError(f"{system_id}: public_api_symbols must be non-empty strings")
        excluded_paths = system.get("excluded_archive_paths", [])
        if not isinstance(excluded_paths, list) or not all(
            isinstance(path, str)
            and path
            and not path.startswith("/")
            and ".." not in Path(path).parts
            for path in excluded_paths
        ):
            raise BaselineSourceError(
                f"{system_id}: excluded_archive_paths must be safe relative paths"
            )
    return contract


def verify_checkout(
    system_id: str,
    system: dict[str, Any],
    source: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    checkout = (project_root / system["checkout"]).resolve()
    baseline_root = (project_root / "raw" / "baselines").resolve()
    if not checkout.is_relative_to(baseline_root) or not checkout.is_dir():
        raise BaselineSourceError(f"{system_id}: checkout is missing or outside baseline root")
    expected_repo = _implementation_repository(source, system["repository_role"])
    head = _git(checkout, "rev-parse", "HEAD")
    if head != system["revision"]:
        raise BaselineSourceError(
            f"{system_id}: HEAD {head} differs from registered {system['revision']}"
        )
    status = _git(checkout, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise BaselineSourceError(f"{system_id}: checkout is dirty")
    origin = _git(checkout, "remote", "get-url", "origin")
    if _normalize_repo_url(origin) != _normalize_repo_url(expected_repo["url"]):
        raise BaselineSourceError(f"{system_id}: origin differs from the source ledger")

    package_file = checkout / system["package_file"]
    package = tomllib.loads(package_file.read_text(encoding="utf-8"))["project"]
    expected_package = {
        "name": system["package"],
        "version": str(system["package_version"]),
        "requires-python": system["python"],
    }
    actual_package = {
        "name": package.get("name"),
        "version": str(package.get("version")),
        "requires-python": package.get("requires-python"),
    }
    if actual_package != expected_package:
        raise BaselineSourceError(f"{system_id}: package metadata mismatch: {actual_package!r}")

    api_files: list[dict[str, Any]] = []
    for prefix in ("public", "secondary"):
        file_key = f"{prefix}_api_file"
        symbols_key = f"{prefix}_api_symbols"
        if file_key not in system:
            continue
        api_path = checkout / system[file_key]
        if not api_path.is_file():
            raise BaselineSourceError(f"{system_id}: API file is missing: {api_path}")
        text = api_path.read_text(encoding="utf-8")
        missing = [symbol for symbol in system[symbols_key] if symbol not in text]
        if missing:
            raise BaselineSourceError(f"{system_id}: API symbols missing: {missing}")
        api_files.append(
            {
                "path": system[file_key],
                "sha256": _sha256_file(api_path),
                "symbols": system[symbols_key],
            }
        )

    license_candidates = [checkout / name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")]
    license_path = next((path for path in license_candidates if path.is_file()), None)
    if license_path is None:
        raise BaselineSourceError(f"{system_id}: repository license file is missing")
    lock_files = [
        path
        for name in ("uv.lock", "poetry.lock", "requirements.txt")
        if (path := checkout / name).is_file()
    ]
    return {
        "system_id": system_id,
        "source_id": system["source_id"],
        "origin": expected_repo["url"],
        "revision": head,
        "tree_sha": _git(checkout, "rev-parse", "HEAD^{tree}"),
        "source_archive_sha256": _git_archive_sha256(checkout, head),
        "clean_checkout": True,
        "license": system["license"],
        "license_file": str(license_path.relative_to(checkout)),
        "license_sha256": _sha256_file(license_path),
        "package": actual_package,
        "package_file_sha256": _sha256_file(package_file),
        "lock_files": [
            {"path": str(path.relative_to(checkout)), "sha256": _sha256_file(path)}
            for path in lock_files
        ],
        "api_files": api_files,
    }


def verify_all(
    contract_path: Path = DEFAULT_CONTRACT,
    ledger_path: Path = DEFAULT_LEDGER,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    contract = load_contract(contract_path, ledger_path)
    ledger = load_and_validate(ledger_path)
    receipts = [
        verify_checkout(
            system_id,
            system,
            ledger["sources"][system["source_id"]],
            project_root=project_root,
        )
        for system_id, system in contract["systems"].items()
    ]
    payload = {
        "schema_version": "1.0",
        "contract": str(contract_path.resolve()),
        "contract_sha256": _sha256_file(contract_path),
        "ledger": str(ledger_path.resolve()),
        "ledger_sha256": _sha256_file(ledger_path),
        "systems": receipts,
    }
    return {
        **payload,
        "receipt_sha256": hashlib.sha256(_canonical_json(payload).encode()).hexdigest(),
    }


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoded = (_canonical_json(payload) + "\n").encode()
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = verify_all(args.contract, args.ledger)
    _write_atomic(args.output.resolve(), receipt)
    print(
        f"memory baseline source preflight PASS: {len(receipt['systems'])} systems, "
        f"receipt={receipt['receipt_sha256']} output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
