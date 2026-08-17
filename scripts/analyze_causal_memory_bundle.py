#!/usr/bin/env python3
"""Verify and analyze one already sealed causal-memory trial bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import TrialBundle, analyze_trials  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    if len(args.manifest_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in args.manifest_sha256
    ):
        raise SystemExit("manifest SHA-256 must be lowercase 64-hex")
    bundle_root = args.bundle_root.resolve()
    actual = sha256_file(bundle_root / "manifest.json")
    if actual != args.manifest_sha256:
        raise SystemExit("raw trial manifest does not match the requested digest")
    report = analyze_trials(
        TrialBundle(root=bundle_root, manifest_sha256=args.manifest_sha256)
    )
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
