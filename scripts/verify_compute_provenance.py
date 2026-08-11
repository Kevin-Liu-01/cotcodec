#!/usr/bin/env python3
"""Verify the executed image's embedded source provenance against the manifest."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

PROVENANCE_PATH = Path("/etc/cotcodec-provenance.json")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def main() -> None:
    expected_git = os.environ.get("COTCODEC_GIT_SHA", "")
    expected_source = os.environ.get("COTCODEC_SOURCE_SHA256", "")
    if not GIT_RE.fullmatch(expected_git) or not SHA_RE.fullmatch(expected_source):
        raise SystemExit("manifest provenance environment is malformed")
    try:
        embedded = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"embedded image provenance is unavailable: {exc}") from exc
    if embedded.get("git_sha") != expected_git:
        raise SystemExit("embedded git SHA does not match the manifest")
    if embedded.get("source_sha256") != expected_source:
        raise SystemExit("embedded source archive hash does not match the manifest")
    print(json.dumps({"status": "PASS", **embedded}, sort_keys=True))


if __name__ == "__main__":
    main()
