#!/usr/bin/env python3
"""Bind a PAST-Bench checkout to its exact longitudinal task surface.

This doctor deliberately does not import or execute upstream code.  It verifies
the Git checkout, parses the declarative family/task/reference manifests, and
emits a content-addressed receipt.  Passing this doctor means that the source is
the registered benchmark source; it is not evidence that a model run succeeded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate  # noqa: E402

DEFAULT_CONTRACT = PROJECT_ROOT / "research" / "source-contracts" / "past-bench.yaml"
ABILITY_DIRS = (
    "memory_ability",
    "procedural_ability",
    "proactive_information_gathering",
    "update_ability",
)
LOCK_FILENAMES = {
    "Cargo.lock",
    "Pipfile.lock",
    "go.sum",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
}


class PastBenchSourceError(ValueError):
    """Raised when the checkout or registered PAST-Bench contract drifts."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _root(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _git(checkout: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PastBenchSourceError(
            f"git {' '.join(args)} failed for {checkout}: {detail}"
        )
    return result.stdout.strip()


def _git_archive_sha256(checkout: Path, revision: str) -> str:
    process = subprocess.Popen(
        ["git", "-C", str(checkout), "archive", "--format=tar", revision],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:
        raise PastBenchSourceError("failed to open git archive pipes")
    digest = hashlib.sha256()
    for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
        digest.update(chunk)
    stderr = process.stderr.read().decode(errors="replace").strip()
    returncode = process.wait()
    if returncode:
        raise PastBenchSourceError(f"git archive failed: {stderr}")
    return digest.hexdigest()


def _normalize_repo_url(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def _mapping_bytes(value_bytes: bytes, *, owner: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(value_bytes.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        raise PastBenchSourceError(f"{owner}: cannot load YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise PastBenchSourceError(f"{owner}: YAML document must be a mapping")
    return value


def _local_mapping(path: Path, *, owner: str) -> dict[str, Any]:
    """Load the caller-owned contract, never an upstream checkout file."""

    try:
        return _mapping_bytes(path.read_bytes(), owner=owner)
    except OSError as exc:
        raise PastBenchSourceError(f"{owner}: cannot read contract: {exc}") from exc


class _IndexedSourceReader:
    """Read only stage-0 Git-index blobs through no-follow file descriptors."""

    def __init__(self, checkout: Path) -> None:
        self.checkout = checkout
        self.object_format = _git(checkout, "rev-parse", "--show-object-format")
        if self.object_format not in {"sha1", "sha256"}:
            raise PastBenchSourceError(
                f"unsupported Git object format: {self.object_format!r}"
            )
        result = subprocess.run(
            ["git", "-C", str(checkout), "ls-files", "-s", "-z"],
            check=False,
            capture_output=True,
        )
        if result.returncode:
            raise PastBenchSourceError(
                "git ls-files failed: "
                + result.stderr.decode(errors="replace").strip()
            )
        self.index: dict[str, tuple[str, str]] = {}
        special: list[str] = []
        for raw in result.stdout.split(b"\0"):
            if not raw:
                continue
            try:
                metadata, path_bytes = raw.split(b"\t", 1)
                mode, object_id, stage = metadata.decode("ascii").split()
                path = path_bytes.decode("utf-8")
            except (UnicodeError, ValueError) as exc:
                raise PastBenchSourceError("malformed Git index entry") from exc
            if stage != "0":
                raise PastBenchSourceError(f"unmerged Git index entry: {path}")
            if mode in {"120000", "160000"}:
                special.append(path)
                continue
            if mode not in {"100644", "100755"}:
                raise PastBenchSourceError(f"unsupported Git mode {mode}: {path}")
            if path in self.index:
                raise PastBenchSourceError(f"duplicate Git index path: {path}")
            self.index[path] = (mode, object_id)
        if special:
            raise PastBenchSourceError(
                "tracked symlinks or gitlinks are not admissible source inputs: "
                f"{special!r}"
            )
        directory_flags = os.O_RDONLY | os.O_DIRECTORY
        if hasattr(os, "O_CLOEXEC"):
            directory_flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            directory_flags |= os.O_NOFOLLOW
        self._directory_flags = directory_flags
        self._file_flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            self._file_flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            self._file_flags |= os.O_NOFOLLOW
        self._root_fd = os.open(checkout, directory_flags)

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self.index))

    def close(self) -> None:
        if self._root_fd >= 0:
            os.close(self._root_fd)
            self._root_fd = -1

    def __enter__(self) -> _IndexedSourceReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def read_bytes(self, relative: str, *, owner: str) -> bytes:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or any(
            part in {"", ".", ".."} for part in pure.parts
        ):
            raise PastBenchSourceError(f"{owner}: unsafe source path {relative!r}")
        registered = self.index.get(pure.as_posix())
        if registered is None:
            raise PastBenchSourceError(f"{owner}: path is not a tracked source file")
        _, expected_object_id = registered

        directory_fd = os.dup(self._root_fd)
        file_fd = -1
        try:
            for part in pure.parts[:-1]:
                next_fd = os.open(part, self._directory_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            file_fd = os.open(pure.parts[-1], self._file_flags, dir_fd=directory_fd)
            metadata = os.fstat(file_fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise PastBenchSourceError(f"{owner}: source is not a regular file")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(file_fd, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
        except OSError as exc:
            raise PastBenchSourceError(f"{owner}: cannot safely read source: {exc}") from exc
        finally:
            if file_fd >= 0:
                os.close(file_fd)
            os.close(directory_fd)

        digest = hashlib.new(self.object_format)
        digest.update(f"blob {len(data)}\0".encode("ascii"))
        digest.update(data)
        if digest.hexdigest() != expected_object_id:
            raise PastBenchSourceError(
                f"{owner}: worktree bytes differ from the registered Git blob"
            )
        return data

    def mapping(self, relative: str, *, owner: str) -> tuple[dict[str, Any], bytes]:
        data = self.read_bytes(relative, owner=owner)
        return _mapping_bytes(data, owner=owner), data


def _directory_receipt(directory: str, source: _IndexedSourceReader) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    prefix = directory.rstrip("/") + "/"
    for relative in (path for path in source.paths if path.startswith(prefix)):
        data = source.read_bytes(relative, owner="task content")
        files.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": _sha256_bytes(data),
            }
        )
    if not files:
        raise PastBenchSourceError(f"task directory is empty: {directory}")
    return {"file_count": len(files), "content_root_sha256": _root(files)}


def _reference_manifest(
    source: _IndexedSourceReader,
    family_id: str,
    family_dir: str,
    episode_order: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config_prefix = "configs/self_evolve_v2/"
    suffix = f"_{family_id.lower()}_only.yaml"
    matches = [
        path
        for path in source.paths
        if path.startswith(config_prefix)
        and "/" not in path.removeprefix(config_prefix)
        and path.endswith(suffix)
    ]
    if len(matches) != 1:
        raise PastBenchSourceError(
            f"{family_id}: expected one reference manifest, found {len(matches)}"
        )
    manifest_path = matches[0]
    manifest, manifest_bytes = source.mapping(
        manifest_path, owner=f"{family_id} reference manifest"
    )
    episodes = manifest.get("episodes")
    if not isinstance(episodes, list) or len(episodes) != len(episode_order):
        raise PastBenchSourceError(
            f"{family_id}: reference manifest episode count differs from family order"
        )

    normalized: list[dict[str, Any]] = []
    seen_task_ids: set[str] = set()
    for index, (expected_dir, episode) in enumerate(zip(episode_order, episodes, strict=True)):
        if not isinstance(episode, dict):
            raise PastBenchSourceError(f"{family_id}: episode {index} must be a mapping")
        if episode.get("family_id") != family_id:
            raise PastBenchSourceError(f"{family_id}: episode {index} family_id drifted")
        task_ref = episode.get("task")
        if not isinstance(task_ref, str) or not task_ref:
            raise PastBenchSourceError(f"{family_id}: episode {index} task is missing")
        raw_task_ref = PurePosixPath(task_ref)
        if raw_task_ref.is_absolute():
            raise PastBenchSourceError(f"{family_id}: absolute task path is forbidden")
        lexical_task_dir = posixpath.normpath(
            posixpath.join(posixpath.dirname(manifest_path), task_ref)
        )
        lexical_expected_dir = f"{family_dir}/{expected_dir}"
        if lexical_task_dir != lexical_expected_dir:
            raise PastBenchSourceError(
                f"{family_id}: episode {index} task path differs from episode_order"
            )
        task_dir = lexical_expected_dir
        task_path = f"{task_dir}/task.yaml"
        task_doc, task_bytes = source.mapping(
            task_path, owner=f"{family_id}/{expected_dir}/task.yaml"
        )
        task_id = task_doc.get("task_id")
        if not isinstance(task_id, str) or not task_id or task_id in seen_task_ids:
            raise PastBenchSourceError(f"{family_id}: invalid or duplicate task_id {task_id!r}")
        seen_task_ids.add(task_id)

        bucket = episode.get("bucket")
        fresh = episode.get("requires_fresh_session")
        persistence_allowed = episode.get("persistence_allowed")
        if bucket in {"evaluation", "control"} and fresh is not True:
            raise PastBenchSourceError(
                f"{family_id}/{expected_dir}: evaluation/control must require a fresh session"
            )
        if "no_persistence" in expected_dir.lower() and persistence_allowed is not False:
            raise PastBenchSourceError(
                f"{family_id}/{expected_dir}: no-persistence control enables persistence"
            )
        if not isinstance(persistence_allowed, bool) or not isinstance(fresh, bool):
            raise PastBenchSourceError(
                f"{family_id}/{expected_dir}: persistence/fresh-session fields must be bool"
            )

        content = _directory_receipt(task_dir, source)
        normalized.append(
            {
                "index": index,
                "family_id": family_id,
                "directory": expected_dir,
                "task_id": task_id,
                "task_yaml_sha256": _sha256_bytes(task_bytes),
                "bucket": bucket,
                "stage": episode.get("stage"),
                "mechanism": episode.get("mechanism"),
                "expected_persistence_signal": episode.get(
                    "expected_persistence_signal"
                ),
                "requires_fresh_session": fresh,
                "persistence_allowed": persistence_allowed,
                "history_mode": episode.get("history_mode"),
                **content,
            }
        )

    return (
        {
            "path": manifest_path,
            "sha256": _sha256_bytes(manifest_bytes),
        },
        normalized,
    )


def inspect_checkout(checkout: Path) -> dict[str, Any]:
    """Inspect a clean checkout without trusting or executing its Python code."""

    checkout = checkout.resolve(strict=True)
    if not checkout.is_dir() or not (checkout / ".git").exists():
        raise PastBenchSourceError("checkout must be a Git working tree")
    status = _git(checkout, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise PastBenchSourceError("checkout must be clean")
    head = _git(checkout, "rev-parse", "HEAD")
    origin = _git(checkout, "remote", "get-url", "origin")
    family_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    unreferenced_rows: list[dict[str, Any]] = []
    category_family_counts: Counter[str] = Counter()
    category_episode_counts: Counter[str] = Counter()
    global_task_ids: set[str] = set()

    with _IndexedSourceReader(checkout) as source:
        framework_prefix = "self-evolve-tasks-v2/"
        present_abilities = sorted(
            {
                PurePosixPath(path).parts[1]
                for path in source.paths
                if path.startswith(framework_prefix)
                and len(PurePosixPath(path).parts) > 1
                and not PurePosixPath(path).parts[1].startswith("_")
            }
        )
        if present_abilities != sorted(ABILITY_DIRS):
            raise PastBenchSourceError(
                f"ability directories drifted: {present_abilities!r}"
            )

        for ability in ABILITY_DIRS:
            ability_prefix = f"{framework_prefix}{ability}/"
            family_paths = [
                path
                for path in source.paths
                if path.startswith(ability_prefix)
                and len(PurePosixPath(path).parts) == 4
                and PurePosixPath(path).name == "family.yaml"
            ]
            for family_path in family_paths:
                family_dir = posixpath.dirname(family_path)
                family_id_from_path = PurePosixPath(family_dir).name
                family, family_bytes = source.mapping(
                    family_path, owner=family_path
                )
                family_id = family.get("family_id")
                if family_id != family_id_from_path:
                    raise PastBenchSourceError(
                        f"{family_dir}: family_id differs from directory"
                    )
                if (
                    family.get("ability_dir") != ability
                    or family.get("primary_ability") != ability
                ):
                    raise PastBenchSourceError(
                        f"{family_id}: ability metadata differs from directory"
                    )
                total = family.get("total_episodes")
                buckets = family.get("instances_per_bucket")
                order = family.get("episode_order")
                if (
                    not isinstance(total, int)
                    or isinstance(total, bool)
                    or total < 1
                    or not isinstance(buckets, dict)
                    or not all(
                        isinstance(key, str)
                        and isinstance(count, int)
                        and not isinstance(count, bool)
                        and count >= 0
                        for key, count in buckets.items()
                    )
                    or sum(buckets.values()) != total
                ):
                    raise PastBenchSourceError(f"{family_id}: invalid episode counts")
                if (
                    not isinstance(order, list)
                    or len(order) != total
                    or len(set(order)) != total
                    or not all(isinstance(item, str) and item for item in order)
                ):
                    raise PastBenchSourceError(f"{family_id}: invalid episode_order")

                family_prefix = family_dir + "/"
                task_dirs = {
                    PurePosixPath(path).parts[3]
                    for path in source.paths
                    if path.startswith(family_prefix)
                    and len(PurePosixPath(path).parts) == 5
                    and PurePosixPath(path).name == "task.yaml"
                }
                missing = set(order) - task_dirs
                if missing:
                    raise PastBenchSourceError(
                        f"{family_id}: episode_order references missing tasks "
                        f"{sorted(missing)!r}"
                    )
                reference, episodes = _reference_manifest(
                    source, family_id, family_dir, order
                )
                for episode in episodes:
                    if episode["task_id"] in global_task_ids:
                        raise PastBenchSourceError(
                            "duplicate task_id across benchmark: "
                            f"{episode['task_id']}"
                        )
                    global_task_ids.add(episode["task_id"])
                    task_rows.append({"ability": ability, **episode})

                undeclared = sorted(task_dirs - set(order))
                for name in undeclared:
                    orphan_dir = f"{family_dir}/{name}"
                    orphan_task, _ = source.mapping(
                        f"{orphan_dir}/task.yaml",
                        owner=f"{family_id}/{name}/task.yaml",
                    )
                    unreferenced_rows.append(
                        {
                            "ability": ability,
                            "family_id": family_id,
                            "directory": name,
                            "task_id": orphan_task.get("task_id"),
                            **_directory_receipt(orphan_dir, source),
                        }
                    )

                family_rows.append(
                    {
                        "ability": ability,
                        "family_id": family_id,
                        "family_yaml_sha256": _sha256_bytes(family_bytes),
                        "total_episodes": total,
                        "instances_per_bucket": dict(sorted(buckets.items())),
                        "episode_order": order,
                        "unreferenced_task_dirs": undeclared,
                        "reference_manifest": reference,
                    }
                )
                category_family_counts[ability] += 1
                category_episode_counts[ability] += total

        required_paths = (
            "LICENSE",
            "README.md",
            "pyproject.toml",
            "requirements.txt",
            "Dockerfile.runtime",
            "Dockerfile.agent",
            "configs/agents.yaml",
        )
        required_files = []
        for relative in required_paths:
            data = source.read_bytes(relative, owner="required source file")
            required_files.append(
                {
                    "path": relative,
                    "size": len(data),
                    "sha256": _sha256_bytes(data),
                }
            )

        lock_files = sorted(
            path for path in source.paths if PurePosixPath(path).name in LOCK_FILENAMES
        )
    family_rows.sort(key=lambda row: (row["ability"], row["family_id"]))
    task_rows.sort(key=lambda row: (row["ability"], row["family_id"], row["index"]))
    unreferenced_rows.sort(
        key=lambda row: (row["ability"], row["family_id"], row["directory"])
    )
    required_files.sort(key=lambda row: row["path"])

    if _git(checkout, "rev-parse", "HEAD") != head:
        raise PastBenchSourceError("checkout HEAD changed during inspection")
    if _git(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise PastBenchSourceError("checkout changed during inspection")

    return {
        "schema_version": 1,
        "status": "INSPECTED_NOT_ADMITTED",
        "scientific_result": False,
        "checkout": {
            "origin": _normalize_repo_url(origin),
            "revision": head,
            "tree_sha": _git(checkout, "rev-parse", "HEAD^{tree}"),
            "source_archive_sha256": _git_archive_sha256(checkout, head),
            "clean": True,
        },
        "category_family_counts": dict(sorted(category_family_counts.items())),
        "category_episode_counts": dict(sorted(category_episode_counts.items())),
        "family_count": len(family_rows),
        "declared_episode_count": len(task_rows),
        "unreferenced_task_count": len(unreferenced_rows),
        "family_roster_sha256": _root(family_rows),
        "task_manifest_sha256": _root(task_rows),
        "unreferenced_task_manifest_sha256": _root(unreferenced_rows),
        "required_files_sha256": _root(required_files),
        "dependency_lock_files": lock_files,
        "families": family_rows,
        "tasks": task_rows,
        "unreferenced_tasks": unreferenced_rows,
        "required_files": required_files,
    }


def load_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    contract = _local_mapping(contract_path, owner="PAST-Bench source contract")
    if contract.get("schema_version") != 1:
        raise PastBenchSourceError("contract schema_version must be 1")
    if contract.get("source_id") != "past-bench":
        raise PastBenchSourceError("contract source_id must be past-bench")
    ledger = load_and_validate(ledger_path)
    source = ledger["sources"].get("past-bench")
    if not isinstance(source, dict):
        raise PastBenchSourceError("past-bench is absent from the source ledger")
    role = contract.get("repository_role")
    repositories = [
        repo for repo in source.get("repositories", []) if repo.get("role") == role
    ]
    if len(repositories) != 1:
        raise PastBenchSourceError("repository_role must resolve exactly once in ledger")
    repository = repositories[0]
    for field in ("url", "revision", "license"):
        if contract.get(field) != repository.get(field):
            raise PastBenchSourceError(f"contract {field} differs from source ledger")
    if contract.get("scientific_result") is not False:
        raise PastBenchSourceError("source admission must not be labeled a scientific result")
    if contract.get("dependency_lock_status") != "unresolved-upstream":
        raise PastBenchSourceError("dependency lock gap must stay explicit")
    expected = contract.get("expected")
    if not isinstance(expected, dict):
        raise PastBenchSourceError("contract expected section must be a mapping")
    return contract


def validate_checkout(
    checkout: Path,
    *,
    contract_path: Path = DEFAULT_CONTRACT,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    """Validate one checkout against the registered source and roster roots."""

    contract = load_contract(contract_path, ledger_path)
    observed = inspect_checkout(checkout)
    checkout_receipt = observed["checkout"]
    expected_checkout = {
        "origin": _normalize_repo_url(contract["url"]),
        "revision": contract["revision"],
        "tree_sha": contract["tree_sha"],
        "source_archive_sha256": contract["source_archive_sha256"],
        "clean": True,
    }
    if checkout_receipt != expected_checkout:
        raise PastBenchSourceError("checkout identity differs from registered source")

    expected = contract["expected"]
    observed_projection = {
        "category_family_counts": observed["category_family_counts"],
        "category_episode_counts": observed["category_episode_counts"],
        "family_count": observed["family_count"],
        "declared_episode_count": observed["declared_episode_count"],
        "unreferenced_task_count": observed["unreferenced_task_count"],
        "family_roster_sha256": observed["family_roster_sha256"],
        "task_manifest_sha256": observed["task_manifest_sha256"],
        "unreferenced_task_manifest_sha256": observed[
            "unreferenced_task_manifest_sha256"
        ],
        "required_files_sha256": observed["required_files_sha256"],
        "dependency_lock_files": observed["dependency_lock_files"],
    }
    if observed_projection != expected:
        raise PastBenchSourceError("declared benchmark surface differs from contract")

    receipt = {
        **observed,
        "status": "VALIDATED_SOURCE_CONTRACT_NOT_EXECUTION",
        "source_id": "past-bench",
        "repository_role": contract["repository_role"],
        "license": contract["license"],
        "dependency_lock_status": contract["dependency_lock_status"],
        "contract_sha256": _sha256_file(contract_path),
        "ledger_sha256": _sha256_file(ledger_path),
    }
    receipt["receipt_sha256"] = _root(receipt)
    return receipt


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (_canonical_json(payload) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise PastBenchSourceError(f"refusing to overwrite output: {path}") from exc
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="print observed roots without admitting the checkout",
    )
    args = parser.parse_args()
    receipt = (
        inspect_checkout(args.checkout)
        if args.inspect_only
        else validate_checkout(
            args.checkout, contract_path=args.contract, ledger_path=args.ledger
        )
    )
    if args.output is not None:
        _write_new(args.output, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
