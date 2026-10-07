#!/usr/bin/env python3
"""Pack, verify or unpack a Q1 study artifact (``harness/q1/study_artifact.py``).

    # host side, in a GPU-less container or plain Python (no torch needed):
    python scripts/q1_study_artifact.py pack --out A.json --repo-revision SHA \\
        --git-tree kernelgym=/src/KernelGYM@3a84417f...:hkust-nlp/KernelGYM:none \\
        --git-tree kbv=/src/kbv@3fdf6fec...:facebookresearch/kernel_bench_verified:MIT \\
        --dir corpus=/runs/pilot-corpus:q1-pilot-corpus:mixed
    # inside a lane job (the lane mounts the file read-only and checks its size and hash):
    python scripts/q1_study_artifact.py unpack --evidence /inputs/study-artifact.json \\
        --expected-evidence-sha256 SHA --out /outputs/inputs

The artifact is host-only run input: it is never committed or pushed (it may
hold an unlicensed fidelity reference such as KernelGYM).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import study_artifact as sa  # noqa: E402


def _split_spec(spec: str) -> tuple[str, str, str, str]:
    name, _, rest = spec.partition("=")
    location, source, licence = rest.rsplit(":", 2)
    if not name or not location:
        raise SystemExit(f"bad tree spec {spec!r}: NAME=LOCATION:SOURCE:LICENCE")
    return name, location, source, licence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack")
    pack.add_argument("--out", type=Path, required=True)
    pack.add_argument("--repo-revision", required=True)
    pack.add_argument("--git-tree", action="append", default=[], help="NAME=CLONE@REV:SOURCE:LIC")
    pack.add_argument("--dir", action="append", default=[], help="NAME=PATH:SOURCE:LICENCE")
    for name in ("verify", "unpack"):
        command = sub.add_parser(name)
        command.add_argument("--evidence", type=Path, required=True)
        command.add_argument("--expected-evidence-sha256", required=True)
        if name == "unpack":
            command.add_argument("--out", type=Path, required=True)
            command.add_argument("--tree", action="append", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "pack":
            trees = {}
            for spec in args.git_tree:
                name, location, source, licence = _split_spec(spec)
                clone, _, revision = location.partition("@")
                trees[name] = sa.git_tree(
                    Path(clone), revision or "HEAD", source=source, licence=licence
                )
            for spec in args.dir:
                name, location, source, licence = _split_spec(spec)
                trees[name] = sa.dir_tree(Path(location), source=source, licence=licence)
            receipt = sa.write(sa.build(trees, repo_revision=args.repo_revision), args.out)
            print(json.dumps(receipt, indent=1, sort_keys=True))
        else:
            document = sa.load(args.evidence, args.expected_evidence_sha256)
            if args.command == "verify":
                print(json.dumps({"status": "PASS", "manifest": document["manifest_sha256"]}))
            else:
                receipt = sa.unpack(document, args.out, names=args.tree)
                print(json.dumps(receipt, indent=1, sort_keys=True))
    except sa.ArtifactError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
