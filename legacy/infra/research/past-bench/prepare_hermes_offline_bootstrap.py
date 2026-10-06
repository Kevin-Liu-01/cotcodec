#!/usr/bin/env python3
"""Prove and seed the exact offline Hermes+ bootstrap marker for PAST-Bench."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

from packaging.requirements import Requirement
from packaging.version import Version
from past_bench.config import load_config
from past_bench.runtime.manager import (
    RuntimeSessionManager,
    _bootstrap_marker_payload,
)
from past_bench.runtime.protocol import BootstrapRequest
from past_bench.runtime.registry import get_agent_spec, load_agent_registry

EXPECTED_COMMANDS = ["pip install -e agents/hermes-plus"]


class OfflineBootstrapError(ValueError):
    """Raised when the sealed image cannot run Hermes+ without network access."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir() or root.is_symlink():
        raise OfflineBootstrapError("Hermes+ source root is missing or unsafe")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise OfflineBootstrapError("Hermes+ source contains a symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise OfflineBootstrapError("Hermes+ source contains a special file")
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if relative.is_absolute() or any(
            part in {"", ".", ".."} for part in relative.parts
        ):
            raise OfflineBootstrapError("Hermes+ source path is unsafe")
        rows.append(
            {
                "path": relative.as_posix(),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    if not rows:
        raise OfflineBootstrapError("Hermes+ source tree is empty")
    return rows


def _direct_dependencies(pyproject: Path) -> list[dict[str, str]]:
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise OfflineBootstrapError("Hermes+ pyproject is invalid") from exc
    project = payload.get("project") if isinstance(payload, dict) else None
    build = payload.get("build-system") if isinstance(payload, dict) else None
    dependency_strings = project.get("dependencies") if isinstance(project, dict) else None
    build_strings = build.get("requires") if isinstance(build, dict) else None
    if not isinstance(dependency_strings, list) or not isinstance(build_strings, list):
        raise OfflineBootstrapError("Hermes+ dependency contracts are missing")
    requirements = [
        *(Requirement(item) for item in build_strings),
        *(Requirement(item) for item in dependency_strings),
    ]
    rows: list[dict[str, str]] = []
    for requirement in requirements:
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        try:
            installed = importlib.metadata.version(requirement.name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise OfflineBootstrapError(
                f"sealed image is missing Hermes+ dependency {requirement.name}"
            ) from exc
        if requirement.specifier and Version(installed) not in requirement.specifier:
            raise OfflineBootstrapError(
                f"sealed image dependency {requirement.name}=={installed} violates "
                f"{requirement.specifier}"
            )
        rows.append(
            {
                "name": requirement.name,
                "required": str(requirement.specifier),
                "installed": installed,
            }
        )
    return sorted(rows, key=lambda row: row["name"].lower())


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
        _fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(*, config_path: Path, cache_dir: Path, output: Path) -> dict[str, Any]:
    config = load_config(config_path)
    if config.runtime.mode != "local" or Path(config.runtime.cache_dir) != cache_dir:
        raise OfflineBootstrapError("PAST runtime config and bootstrap cache differ")
    registry_path = Path(config.runtime.registry_path).resolve()
    registry = load_agent_registry(registry_path)
    spec = get_agent_spec("hermes-plus", registry)
    if (
        spec.adapter != "hermes"
        or spec.install_policy != "pip"
        or spec.bootstrap_commands != EXPECTED_COMMANDS
    ):
        raise OfflineBootstrapError("registered Hermes+ bootstrap contract drifted")

    hermes_root = Path("agents/hermes-plus").resolve()
    pyproject = hermes_root / "pyproject.toml"
    dependencies = _direct_dependencies(pyproject)
    source_manifest = _tree_manifest(hermes_root)
    sys.path.insert(0, str(hermes_root))
    for module_name in ("run_agent", "hermes_state"):
        importlib.import_module(module_name)

    marker_payload = _bootstrap_marker_payload(spec)
    if marker_payload != {
        "install_policy": "pip",
        "python_executable": "/opt/past-bench-venv/bin/python",
    }:
        raise OfflineBootstrapError("Hermes+ bootstrap marker contract drifted")
    marker = cache_dir / "hermes-plus.ready"
    marker_bytes = _canonical(marker_payload)
    if marker.exists() or marker.is_symlink():
        if marker.is_symlink() or not marker.is_file() or marker.read_bytes() != marker_bytes:
            raise OfflineBootstrapError("existing Hermes+ bootstrap marker drifted")
    else:
        _write_once(marker, marker_bytes)

    manager = RuntimeSessionManager(registry_path=registry_path, cache_dir=cache_dir)
    response = manager.bootstrap(BootstrapRequest(agent_name="hermes-plus"))
    if not response.already_present or response.commands_run:
        raise OfflineBootstrapError("Hermes+ attempted a runtime installation")
    report = {
        "schema_version": 1,
        "status": "PAST_HERMES_PLUS_OFFLINE_BOOTSTRAP_PASS",
        "scientific_result": False,
        "network_required": False,
        "python_executable": sys.executable,
        "registry_sha256": _sha256(registry_path),
        "pyproject_sha256": _sha256(pyproject),
        "source_manifest_sha256": hashlib.sha256(_canonical(source_manifest)).hexdigest(),
        "source_file_count": len(source_manifest),
        "direct_dependencies": dependencies,
        "bootstrap_commands_skipped": EXPECTED_COMMANDS,
        "marker_sha256": hashlib.sha256(marker_bytes).hexdigest(),
    }
    _write_once(output, _canonical(report) + b"\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = prepare(
            config_path=args.config, cache_dir=args.cache_dir, output=args.output
        )
    except OfflineBootstrapError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
