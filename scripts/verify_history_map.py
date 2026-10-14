"""Verify and use the commit map written by the 2026-10-14 history rewrite.

The purge ran `git filter-repo --preserve-commit-hashes`, so a rewritten commit differs from
the original only in its parent ids, unless the purge also changed its tree. For every row of
the map this script rebuilds the original commit object from the rewritten one (parents mapped
back through the map, tree, author, committer and message unchanged), hashes it, and compares
the result with the recorded old id. A match proves that the old commit and the new commit
hold the same tree and metadata. A mismatch is expected only for the commits whose tree the
purge changed (listed with their reason in the map's README,
program/history-rewrite-2026-10-14/README.md: 44 pre-restart commits that held
the host address or the inventory, and 11 commits of 2026-10-07 that held the early gate_b.py).

Usage:
  python scripts/verify_history_map.py verify MAP.tsv [--repo PATH] [--expect-changed N]
  python scripts/verify_history_map.py resolve MAP.tsv OLD_ID_OR_PREFIX

MAP.tsv: one "old new" pair per line (40-hex each), as written from filter-repo's commit-map.
No network access; reads only the local repository.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


def read_map(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[0] == "old":
            continue
        old, new = parts
        if len(old) != 40 or len(new) != 40:
            raise SystemExit(f"bad map row: {line!r}")
        pairs[old] = new
    return pairs


class Objects:
    def __init__(self, repo: Path) -> None:
        self.proc = subprocess.Popen(
            ["git", "-C", str(repo), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    def raw(self, oid: str) -> tuple[str, bytes]:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(oid.encode() + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().split()
        if len(header) < 3:
            raise SystemExit(f"object {oid} is missing from the repository")
        size = int(header[2])
        body = self.proc.stdout.read(size)
        self.proc.stdout.read(1)
        return header[1].decode(), body


def verify(map_path: Path, repo: Path, expect_changed: int | None) -> int:
    old_to_new = read_map(map_path)
    new_to_old = {new: old for old, new in old_to_new.items()}
    objects = Objects(repo)
    same = 0
    changed: list[str] = []
    for old, new in old_to_new.items():
        kind, body = objects.raw(new)
        if kind != "commit":
            raise SystemExit(f"{new} is a {kind}, not a commit")
        header, sep, message = body.partition(b"\n\n")
        lines = []
        for line in header.split(b"\n"):
            if line.startswith(b"parent "):
                parent = line[7:].decode()
                line = b"parent " + new_to_old.get(parent, parent).encode()
            lines.append(line)
        rebuilt = b"\n".join(lines) + sep + message
        digest = hashlib.sha1(b"commit %d\0" % len(rebuilt) + rebuilt).hexdigest()
        if digest == old:
            same += 1
        else:
            changed.append(old)
    print(f"rows: {len(old_to_new)}")
    print(f"old id rebuilt exactly (same tree and metadata): {same}")
    print(f"old id not rebuilt (tree changed by the purge): {len(changed)}")
    for old in sorted(changed):
        print(f"  changed {old}")
    if expect_changed is not None and len(changed) != expect_changed:
        print(f"FAIL: expected {expect_changed} changed commits", file=sys.stderr)
        return 1
    return 0


def resolve(map_path: Path, query: str) -> int:
    old_to_new = read_map(map_path)
    hits = sorted(old for old in old_to_new if old.startswith(query.lower()))
    if not hits:
        print(f"{query}: not in the map (not rewritten, or not a commit of this repository)")
        return 1
    if len(hits) > 1:
        print(f"{query}: ambiguous ({len(hits)} matches)")
        return 1
    print(f"{hits[0]} -> {old_to_new[hits[0]]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("verify")
    v.add_argument("map", type=Path)
    v.add_argument("--repo", type=Path, default=Path("."))
    v.add_argument("--expect-changed", type=int)
    r = sub.add_parser("resolve")
    r.add_argument("map", type=Path)
    r.add_argument("query")
    args = parser.parse_args(argv)
    if args.command == "verify":
        return verify(args.map, args.repo, args.expect_changed)
    return resolve(args.map, args.query)


if __name__ == "__main__":
    raise SystemExit(main())
