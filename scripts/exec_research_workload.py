#!/usr/bin/env python3
"""Execute the validated research argv without invoking a user-controlled shell."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

MODEL_CACHE_MOUNT = Path("/model-cache")


def check_model_mount(environ: Mapping[str, str], model_cache: Path = MODEL_CACHE_MOUNT) -> None:
    """Refuse a no-model job (COTCODEC_MODEL_ID=none) that can still see a model cache."""

    if environ.get("COTCODEC_MODEL_ID") == "none" and (
        model_cache.exists() or model_cache.is_symlink()
    ):
        raise SystemExit(f"COTCODEC_MODEL_ID=none but a model cache is mounted at {model_cache}")


def main() -> None:
    check_model_mount(os.environ)
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
