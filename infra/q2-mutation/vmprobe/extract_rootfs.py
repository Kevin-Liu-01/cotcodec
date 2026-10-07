#!/usr/bin/env python3
"""Copy the VM's userland out of its root partition, without root or a mount.

The LibreOffice reachability image is built from these files so that the
GUI-faithful save runs the VM's own LibreOffice build (Ubuntu
1:7.3.7-0ubuntu0.22.04.4), libraries, fonts, Python, pyautogui and user
profile. Only the trees in TREES are copied; the user's home directory is
not, apart from the LibreOffice profile. Ownership becomes the invoking user
(debugfs cannot chown); modes and symlinks are kept.

Writes <out>/rootfs/ and <out>/rootfs-manifest.json (per-tree file counts and
bytes, the merged-/usr symlinks, and a SHA-256 over the sorted file list with
per-file SHA-256).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

TREES = ["/usr", "/etc", "/var/lib/dpkg", "/home/user/.config/libreoffice"]
TOP_LINKS = ["/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32"]


def debugfs(raw: str, request: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["debugfs", "-R", request, raw], capture_output=True, text=True, check=False
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    rootfs = out / "rootfs"
    rootfs.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"trees": {}, "links": {}}
    for link in TOP_LINKS:
        stat = debugfs(args.raw, f"stat {link}").stdout
        match = re.search(r'Fast link dest: "([^"]+)"', stat)
        if match:
            target = rootfs / link.lstrip("/")
            if not target.is_symlink():
                os.symlink(match.group(1), target)
            manifest["links"][link] = match.group(1)
    for tree in TREES:
        parent = rootfs / Path(tree.lstrip("/")).parent
        parent.mkdir(parents=True, exist_ok=True)
        result = debugfs(args.raw, f"rdump {tree} {parent}")
        files = [
            p for p in (rootfs / tree.lstrip("/")).rglob("*") if p.is_file() and not p.is_symlink()
        ]
        manifest["trees"][tree] = {
            "files": len(files),
            "bytes": sum(p.stat().st_size for p in files),
            "debugfs_stderr_lines": len(result.stderr.splitlines()),
        }
    for name in ("tmp", "var/tmp", "run", "proc", "sys", "dev", "home/user"):
        (rootfs / name).mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    count = 0
    for path in sorted(rootfs.rglob("*")):
        rel = path.relative_to(rootfs).as_posix()
        if path.is_symlink():
            digest.update(f"L {rel} {os.readlink(path)}\n".encode())
        elif path.is_file():
            file_hash = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    file_hash.update(chunk)
            digest.update(f"F {rel} {file_hash.hexdigest()}\n".encode())
            count += 1
    manifest["files_total"] = count
    manifest["tree_sha256"] = digest.hexdigest()
    (out / "rootfs-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({"files": count, "tree_sha256": manifest["tree_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
