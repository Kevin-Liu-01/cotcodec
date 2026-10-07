#!/usr/bin/env python3
"""Create a deterministic discovery or clean publication source archive.

Both archives hold regular files only. A discovery archive leaves out a
tracked symlink only under a reviewed agent-tooling prefix, and only when its
relative target names content that the archive already holds; the receipt
records every omitted link. Every other symlink is refused.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import posixpath
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

# Reviewed prefixes under which a tracked symlink may be left out of a
# discovery archive. `.agents/skills/*` mirrors `.claude/skills/*` for the
# universal AgentSkills path; no harness, script, image or workload reads
# `.agents/` at run time. scripts/extract_discovery_source_archive.py holds the
# same tuple and refuses a receipt that records a different one.
OMITTABLE_SYMLINK_PREFIXES: tuple[str, ...] = (".agents/",)
DISCOVERY_SCHEMA_VERSION = 3
PUBLICATION_SCHEMA_VERSION = 2
REGULAR_INDEX_MODES = frozenset({"100644", "100755"})
SYMLINK_INDEX_MODE = "120000"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *arguments: str, text: bool = False) -> bytes | str:
    return subprocess.check_output(
        ["git", *arguments],
        cwd=root,
        text=text,
    )


def _require_repository_root(root: Path) -> None:
    actual = Path(str(_git(root, "rev-parse", "--show-toplevel", text=True)).strip())
    if actual.resolve() != root:
        raise ValueError(f"root must be the Git worktree root: {actual}")


def git_status(root: Path) -> bytes:
    return bytes(
        _git(
            root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "-z",
        )
    )


def _index_modes(root: Path) -> dict[PurePosixPath, frozenset[str]]:
    """Return every index entry's file modes (more than one only mid-merge)."""

    raw = subprocess.run(
        ["git", "ls-files", "-s", "-z", "--", "."],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    modes: dict[PurePosixPath, set[str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, path_bytes = record.partition(b"\t")
        if not separator:
            raise ValueError("Git index emitted a malformed entry")
        try:
            mode = metadata.split(b" ", 1)[0].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("Git index emitted an undecodable entry") from exc
        modes.setdefault(PurePosixPath(os.fsdecode(path_bytes)), set()).add(mode)
    return {path: frozenset(values) for path, values in modes.items()}


def omitted_symlink_target(link: PurePosixPath, target: str) -> PurePosixPath:
    """Return the repository-relative path an omittable link names, or raise.

    The rule is lexical, so the extractor applies it to a receipt unchanged: the
    link sits under a reviewed prefix, its target is relative, and the target
    stays inside the repository without naming the root or the link's own
    directories.
    """

    if not any(link.as_posix().startswith(prefix) for prefix in OMITTABLE_SYMLINK_PREFIXES):
        raise ValueError(
            "source archive forbids symlinks outside the reviewed agent-tooling "
            f"prefixes {list(OMITTABLE_SYMLINK_PREFIXES)}: {link}"
        )
    if not target or "\0" in target:
        raise ValueError(f"symlink target is empty or malformed: {link}")
    if target.startswith("/"):
        raise ValueError(f"symlink target must be relative: {link} -> {target}")
    normalized = posixpath.normpath(posixpath.join(link.parent.as_posix(), target))
    if normalized in {".", ".."} or normalized.startswith("../"):
        raise ValueError(
            f"symlink target escapes the repository or names its root: {link} -> {target}"
        )
    resolved = PurePosixPath(normalized)
    if resolved == link or resolved in link.parents:
        raise ValueError(f"symlink target contains the link itself: {link} -> {target}")
    return resolved


def _omittable_symlink(
    root: Path,
    link: PurePosixPath,
    archived: frozenset[PurePosixPath],
    index_modes: dict[PurePosixPath, frozenset[str]],
) -> dict[str, str]:
    """Check one discovery symlink against the omission rule and return its record."""

    if index_modes.get(link) != frozenset({SYMLINK_INDEX_MODE}):
        raise ValueError(f"source archive forbids symlinks that are not tracked as links: {link}")
    target = os.readlink(root.joinpath(*link.parts))
    resolved = omitted_symlink_target(link, target)
    current = root
    for part in resolved.parts:
        current = current / part
        try:
            status = current.lstat()
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise ValueError(f"symlink target is dangling: {link} -> {target}") from exc
        if stat.S_ISLNK(status.st_mode):
            raise ValueError(f"symlink target passes through another symlink: {link} -> {target}")

    def archived_tracked_file(path: PurePosixPath) -> bool:
        modes = index_modes.get(path, frozenset())
        return path in archived and bool(modes) and modes <= REGULAR_INDEX_MODES

    if stat.S_ISREG(status.st_mode):
        holds_target = archived_tracked_file(resolved)
    elif stat.S_ISDIR(status.st_mode):
        holds_target = any(
            resolved in path.parents and archived_tracked_file(path) for path in archived
        )
    else:
        holds_target = False
    if not holds_target:
        raise ValueError(
            "symlink target is not a tracked regular file or a directory of tracked "
            f"regular files that the archive holds: {link} -> {target}"
        )
    return {"path": link.as_posix(), "target": target}


def discovery_inventory(
    root: Path,
) -> tuple[tuple[PurePosixPath, ...], tuple[dict[str, str], ...]]:
    """Return discovery-mode worktree files and the tracked links left out.

    Files include untracked research code; `data/` is excluded. A symlink is
    left out only under the omission rule above and is otherwise refused.
    """

    completed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z", "--", "."],
        cwd=root,
        check=True,
        capture_output=True,
    )
    paths: list[PurePosixPath] = []
    links: list[PurePosixPath] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        text = os.fsdecode(raw_path)
        path = PurePosixPath(text)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe source path: {text!r}")
        if path.parts and path.parts[0] == "data":
            continue
        absolute = root.joinpath(*path.parts)
        if absolute.is_symlink():
            links.append(path)
            continue
        if not absolute.is_file():
            raise ValueError(f"source path is not a regular file: {path}")
        paths.append(path)
    archived = frozenset(paths)
    index_modes = _index_modes(root) if links else {}
    omitted = [_omittable_symlink(root, link, archived, index_modes) for link in links]
    return (
        tuple(sorted(paths, key=lambda item: item.as_posix().encode())),
        tuple(sorted(omitted, key=lambda row: row["path"].encode())),
    )


def omitted_symlinks_sha256(rows: list[dict[str, str]] | tuple[dict[str, str], ...]) -> str:
    return sha256_bytes(json.dumps(list(rows), sort_keys=True, separators=(",", ":")).encode())


def publication_tree(root: Path, ref: str) -> tuple[dict[str, str], ...]:
    raw = bytes(_git(root, "ls-tree", "-r", "-z", "--full-tree", ref))
    entries: list[dict[str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, path_bytes = record.partition(b"\t")
        if not separator:
            raise ValueError("Git tree emitted a malformed entry")
        try:
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path_text = os.fsdecode(path_bytes)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Git tree emitted an undecodable entry") from exc
        path = PurePosixPath(path_text)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe committed source path: {path_text!r}")
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(
                f"publication archive permits only regular committed files: {path_text}"
            )
        contents = bytes(_git(root, "cat-file", "blob", object_id))
        entries.append(
            {
                "mode": mode,
                "object_id": object_id,
                "path": path_text,
                "sha256": sha256_bytes(contents),
            }
        )
    if not entries:
        raise ValueError("publication archive would be empty")
    return tuple(entries)


def _write_publication_archive(root: Path, ref: str, output: Path) -> None:
    process = subprocess.Popen(
        ["git", "archive", "--format=tar", ref],
        cwd=root,
        stdout=subprocess.PIPE,
    )
    assert process.stdout is not None
    with output.open("xb") as raw_output:
        with gzip.GzipFile(filename="", fileobj=raw_output, mode="wb", mtime=0) as zipped:
            for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
                zipped.write(chunk)
        raw_output.flush()
        os.fsync(raw_output.fileno())
    return_code = process.wait()
    if return_code != 0:
        output.unlink(missing_ok=True)
        raise subprocess.CalledProcessError(return_code, process.args)


def archive_file_manifest(path: Path) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        with gzip.open(path, "rb") as stream, tarfile.open(fileobj=stream, mode="r:") as archive:
            for member in archive:
                member_path = PurePosixPath(member.name)
                if (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or member.name in seen
                ):
                    raise ValueError(f"publication archive has unsafe member: {member.name}")
                seen.add(member.name)
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(
                        f"publication archive permits only files/directories: {member.name}"
                    )
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ValueError(f"publication archive member is unreadable: {member.name}")
                rows.append(
                    {
                        "mode": "100755" if member.mode & 0o111 else "100644",
                        "path": member.name,
                        "sha256": sha256_bytes(extracted.read()),
                    }
                )
    except (gzip.BadGzipFile, tarfile.TarError, EOFError) as exc:
        raise ValueError("publication source archive is not valid gzip-compressed tar") from exc
    return tuple(sorted(rows, key=lambda row: row["path"].encode()))


def _write_discovery_archive(
    root: Path,
    paths: tuple[PurePosixPath, ...],
    output: Path,
) -> None:
    with output.open("xb") as raw_output:
        with (
            gzip.GzipFile(filename="", fileobj=raw_output, mode="wb", mtime=0) as zipped,
            tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive,
        ):
            for relative in paths:
                source = root.joinpath(*relative.parts)
                stat = source.stat()
                info = tarfile.TarInfo(relative.as_posix())
                info.size = stat.st_size
                info.mode = 0o755 if stat.st_mode & 0o111 else 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                with source.open("rb") as stream:
                    archive.addfile(info, stream)
        raw_output.flush()
        os.fsync(raw_output.fileno())


def _atomic_output(output: Path, writer) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.name}.", dir=output.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    temporary_path.unlink()
    try:
        writer(temporary_path)
        try:
            os.link(temporary_path, output)
        except FileExistsError as exc:
            raise ValueError(f"refusing to overwrite source archive: {output}") from exc
        temporary_path.unlink()
        directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Durably publish a source receipt without replacing an existing artifact."""

    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n"

    def writer(temporary: Path) -> None:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

    _atomic_output(path.resolve(), writer)


def create_archive(
    root: Path,
    output: Path,
    *,
    mode: str = "discovery",
    ref: str = "HEAD",
) -> dict[str, Any]:
    """Create an archive and return the complete deterministic source receipt."""

    root = root.resolve(strict=True)
    output = output.resolve()
    _require_repository_root(root)
    if output.exists():
        raise ValueError(f"refusing to overwrite source archive: {output}")
    if mode not in {"discovery", "publication"}:
        raise ValueError("source archive mode must be discovery or publication")

    git_head = str(_git(root, "rev-parse", "HEAD", text=True)).strip()
    selected_sha = str(_git(root, "rev-parse", f"{ref}^{{commit}}", text=True)).strip()
    git_tree = str(_git(root, "rev-parse", f"{selected_sha}^{{tree}}", text=True)).strip()
    omitted: tuple[dict[str, str], ...] = ()
    if mode == "publication":
        before_status = git_status(root)
        if before_status:
            raise ValueError("publication source archive requires a completely clean worktree")
        if selected_sha != git_head:
            raise ValueError("publication source ref must resolve to the checked-out HEAD")
        tree_entries = publication_tree(root, selected_sha)
        entries = tuple(
            {key: row[key] for key in ("mode", "path", "sha256")}
            for row in tree_entries
        )
        file_manifest_sha256 = sha256_bytes(
            json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
        )
        uv_lock = bytes(_git(root, "show", f"{selected_sha}:uv.lock"))
        _atomic_output(
            output,
            lambda temporary: _write_publication_archive(
                root, selected_sha, temporary
            ),
        )
        if archive_file_manifest(output) != entries:
            output.unlink(missing_ok=True)
            raise ValueError(
                "git archive bytes differ from the committed file tree; "
                "export-ignore/export-subst are forbidden"
            )
        if git_status(root) != before_status or str(
            _git(root, "rev-parse", "HEAD", text=True)
        ).strip() != git_head:
            output.unlink(missing_ok=True)
            raise ValueError("source worktree changed while publication archive was built")
        file_count = len(entries)
        archive_format = "git-archive-tar+gzip-mtime-zero"
        worktree_clean = True
        data_excluded = False
    else:
        paths, omitted = discovery_inventory(root)
        if not paths:
            raise ValueError("source archive would be empty")
        _atomic_output(
            output,
            lambda temporary: _write_discovery_archive(root, paths, temporary),
        )
        manifest_rows = [path.as_posix() for path in paths]
        file_manifest_sha256 = sha256_bytes(
            json.dumps(manifest_rows, separators=(",", ":")).encode()
        )
        uv_lock_path = root / "uv.lock"
        uv_lock = uv_lock_path.read_bytes() if uv_lock_path.is_file() else b""
        file_count = len(paths)
        archive_format = "normalized-worktree-tar+gzip-mtime-zero"
        worktree_clean = not bool(git_status(root))
        data_excluded = True

    # Discovery receipts (schema 3) also record the reviewed omission rule and
    # every link it left out. Identity is unchanged: archive_sha256 hashes the
    # archive bytes and file_manifest_sha256 the archived paths, neither of
    # which includes an omitted link. Publication receipts stay at schema 2.
    discovery = mode == "discovery"
    symlink_fields: dict[str, Any] = (
        {
            "omittable_symlink_prefixes": list(OMITTABLE_SYMLINK_PREFIXES),
            "omitted_symlinks": list(omitted),
            "omitted_symlinks_sha256": omitted_symlinks_sha256(omitted),
        }
        if discovery
        else {}
    )
    return {
        "schema_version": DISCOVERY_SCHEMA_VERSION if discovery else PUBLICATION_SCHEMA_VERSION,
        "mode": mode,
        "archive": str(output),
        "archive_sha256": sha256_file(output),
        "archive_format": archive_format,
        "file_count": file_count,
        "file_manifest_sha256": file_manifest_sha256,
        "file_manifest": entries if mode == "publication" else manifest_rows,
        "git_sha": selected_sha,
        "git_tree": git_tree,
        "selected_ref": ref,
        "uv_lock_sha256": sha256_bytes(uv_lock),
        "worktree_clean": worktree_clean,
        "data_excluded": data_excluded,
        "metadata_normalized": True,
        **symlink_fields,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discovery", action="store_true")
    mode.add_argument("--publication", action="store_true")
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Commit/ref to archive; publication mode requires it to equal checked-out HEAD.",
    )
    args = parser.parse_args()
    receipt = create_archive(
        args.root,
        args.output,
        mode="publication" if args.publication else "discovery",
        ref=args.ref,
    )
    if args.receipt is not None:
        if args.receipt.resolve() == args.output.resolve():
            parser.error("source archive and receipt outputs must be distinct")
        try:
            write_receipt(args.receipt, receipt)
        except ValueError as exc:
            parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
