#!/usr/bin/env python3
"""Create a deterministic discovery or clean publication source archive."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


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


def source_paths(root: Path) -> tuple[PurePosixPath, ...]:
    """Return discovery-mode worktree paths, including untracked research code."""

    completed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z", "--", "."],
        cwd=root,
        check=True,
        capture_output=True,
    )
    paths: list[PurePosixPath] = []
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
            raise ValueError(f"source archive forbids symlinks: {path}")
        if not absolute.is_file():
            raise ValueError(f"source path is not a regular file: {path}")
        paths.append(path)
    return tuple(sorted(paths, key=lambda item: item.as_posix().encode()))


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
        paths = source_paths(root)
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

    return {
        "schema_version": 2,
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
