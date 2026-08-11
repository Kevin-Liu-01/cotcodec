#!/usr/bin/env python3
"""Execute the validated research argv without invoking a user-controlled shell."""

from __future__ import annotations

import json
import os


def main() -> None:
    raw = os.environ.get("COTCODEC_COMMAND_JSON_HEX", "")
    try:
        argv = json.loads(bytes.fromhex(raw))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid COTCODEC_COMMAND_JSON_HEX: {exc}") from exc
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        raise SystemExit("decoded workload must be a nonempty JSON argv list")
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
