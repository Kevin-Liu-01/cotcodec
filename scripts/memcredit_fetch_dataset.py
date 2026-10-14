#!/usr/bin/env python3
"""Fetch one pinned file of a public Hugging Face dataset and write a receipt (decision D1).

AM1 Step 0 (EXPLORATORY) uses it for LongMemEval-S (``xiaowu0162/longmemeval-cleaned``,
``longmemeval_s_cleaned.json``). The file is downloaded from the dataset's ``resolve`` URL at a
pinned 40-hex revision, streamed to a temporary file next to its destination while its SHA-256
is computed, checked against the expected size and SHA-256 (the Git LFS oid that the Hub API
lists for that revision), made read-only and renamed into place. An existing file is never
overwritten: if it is already there it is re-verified and the receipt says so.

Subcommands:

* ``fetch``: download (or re-verify) and write the receipt.
* ``verify``: re-hash an existing file against a receipt.

No token is sent; the dataset must be public. The receipt records the source URL, revision,
size, SHA-256, licence (from the Hub card at that revision), timestamps and the API listing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HUB = "https://huggingface.co"


class FetchError(RuntimeError):
    """The download or its verification failed."""


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_url(repo: str, revision: str, filename: str) -> str:
    return f"{HUB}/datasets/{repo}/resolve/{revision}/{filename}"


def validate_args(repo: str, revision: str, filename: str, sha256: str, size: int) -> None:
    if not REPO_RE.fullmatch(repo):
        raise FetchError(f"unsafe dataset repo id {repo!r}")
    if not REVISION_RE.fullmatch(revision):
        raise FetchError("revision must be a pinned 40-hex commit")
    if not FILENAME_RE.fullmatch(filename):
        raise FetchError(f"unsafe filename {filename!r}")
    if not SHA_RE.fullmatch(sha256):
        raise FetchError("expected SHA-256 must be 64 lowercase hex characters")
    if size <= 0:
        raise FetchError("expected size must be positive")


def api_listing(client: Any, repo: str, revision: str, filename: str) -> dict[str, Any]:
    """The Hub's own record of the file (size, LFS oid) and the card licence at the revision."""

    record: dict[str, Any] = {}
    tree = client.get(f"{HUB}/api/datasets/{repo}/tree/{revision}", timeout=60.0)
    tree.raise_for_status()
    for entry in tree.json():
        if entry.get("path") == filename:
            lfs = entry.get("lfs") or {}
            record["tree_size"] = entry.get("size")
            record["tree_lfs_oid"] = lfs.get("oid")
            record["tree_oid"] = entry.get("oid")
    info = client.get(f"{HUB}/api/datasets/{repo}/revision/{revision}", timeout=60.0)
    info.raise_for_status()
    data = info.json()
    record["revision_sha"] = data.get("sha")
    record["last_modified"] = data.get("lastModified")
    record["card_license"] = (data.get("cardData") or {}).get("license")
    record["tags"] = [t for t in data.get("tags", []) if t.startswith("license:")]
    return record


def stream_download(client: Any, url: str, temporary: Path) -> tuple[str, int, str]:
    digest = hashlib.sha256()
    size = 0
    with client.stream("GET", url, follow_redirects=True, timeout=600.0) as response:
        response.raise_for_status()
        final_host = response.url.host
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    return digest.hexdigest(), size, final_host


def fetch(args: argparse.Namespace) -> dict[str, Any]:
    import httpx

    validate_args(args.repo, args.revision, args.filename, args.expected_sha256, args.expected_size)
    dest_dir = Path(args.dest_root) / args.revision
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / args.filename
    url = resolve_url(args.repo, args.revision, args.filename)
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "kind": "public-dataset-file",
        "decision": "D1",
        "repo_id": args.repo,
        "repo_type": "dataset",
        "revision": args.revision,
        "filename": args.filename,
        "source_url": url,
        "license_declared": args.license,
        "expected_sha256": args.expected_sha256,
        "expected_size": args.expected_size,
        "path": str(dest),
        "started_at": utc_now(),
    }
    with httpx.Client(headers={"user-agent": "cotcodec-memcredit-fetch/1"}) as client:
        receipt["hub_api"] = api_listing(client, args.repo, args.revision, args.filename)
        api = receipt["hub_api"]
        if api.get("revision_sha") != args.revision:
            raise FetchError("the Hub does not resolve the revision to itself")
        if api.get("tree_size") != args.expected_size or api.get("tree_lfs_oid") != (
            args.expected_sha256
        ):
            raise FetchError(f"the Hub listing differs from the expected file: {api}")
        if dest.exists():
            receipt["action"] = "existing file re-verified"
        else:
            temporary = dest_dir / f".{args.filename}.part-{os.getpid()}"
            started = time.time()
            try:
                sha, size, host = stream_download(client, url, temporary)
                receipt["download_s"] = round(time.time() - started, 1)
                receipt["download_final_host"] = host
                if size != args.expected_size or sha != args.expected_sha256:
                    raise FetchError(f"downloaded file differs: size {size}, sha256 {sha}")
                temporary.chmod(0o400)
                os.replace(temporary, dest)
            finally:
                if temporary.exists():
                    temporary.unlink()
            receipt["action"] = "downloaded"
    size = dest.stat().st_size
    sha = sha256_file(dest)
    if size != args.expected_size or sha != args.expected_sha256:
        raise FetchError(f"file on disk differs: size {size}, sha256 {sha}")
    receipt.update(size_bytes=size, sha256=sha, verified_at=utc_now())
    receipt_path = Path(args.receipt)
    if receipt_path.exists():
        raise FetchError(f"refusing to overwrite the receipt {receipt_path}")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def verify(args: argparse.Namespace) -> dict[str, Any]:
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    path = Path(args.path or receipt["path"])
    size = path.stat().st_size
    sha = sha256_file(path)
    ok = size == receipt["size_bytes"] and sha == receipt["sha256"]
    result = {"path": str(path), "size_bytes": size, "sha256": sha, "ok": ok}
    if not ok:
        raise FetchError(f"verification failed: {result}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch_parser = sub.add_parser("fetch", allow_abbrev=False)
    fetch_parser.add_argument("--repo", required=True)
    fetch_parser.add_argument("--revision", required=True)
    fetch_parser.add_argument("--filename", required=True)
    fetch_parser.add_argument("--expected-sha256", required=True)
    fetch_parser.add_argument("--expected-size", type=int, required=True)
    fetch_parser.add_argument("--license", required=True)
    fetch_parser.add_argument("--dest-root", required=True)
    fetch_parser.add_argument("--receipt", required=True)
    verify_parser = sub.add_parser("verify", allow_abbrev=False)
    verify_parser.add_argument("--receipt", required=True)
    verify_parser.add_argument("--path", default=None)
    args = parser.parse_args()
    result = fetch(args) if args.command == "fetch" else verify(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
