#!/usr/bin/env python3
"""Write build provenance from Docker build arguments."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: write_provenance.py <output>")
    payload = {
        "git_sha": os.environ.get("GIT_SHA_VALUE", "unknown"),
        "source_sha256": os.environ.get("SOURCE_SHA_VALUE", "unknown"),
    }
    Path(sys.argv[1]).write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
